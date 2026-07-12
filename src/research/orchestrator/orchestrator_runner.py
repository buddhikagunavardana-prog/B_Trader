import time
import traceback

from src.research.orchestrator.orchestrator_context import (
    build_orchestrator_context,
)
from src.research.orchestrator.orchestrator_plan import (
    build_plan,
    summarize_plan,
)
from src.research.orchestrator.orchestrator_registry import (
    build_default_stage_registry,
)
from src.research.orchestrator.orchestrator_report import (
    write_artifact_manifest,
    write_stage_report,
    write_summary_report,
)
from src.research.orchestrator.orchestrator_result import OrchestratorResult
from src.research.orchestrator.orchestrator_stage import (
    STAGE_BLOCKED,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_SKIPPED,
)
from src.research.orchestrator.orchestrator_state import (
    OrchestratorState,
    calculate_config_hash,
    load_state,
    save_state_atomic,
    validate_completed_stage_artifacts,
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _make_result(
    context,
    plan,
    state: OrchestratorState | None,
    status: str,
    started_at: str,
    started_seconds: float,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict | None = None,
) -> OrchestratorResult:
    completed_at = _now()
    elapsed_seconds = round(time.perf_counter() - started_seconds, 6)

    return OrchestratorResult(
        run_id=context.run_id,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_seconds=elapsed_seconds,
        planned_stages=list(plan.execution_order) if plan else [],
        completed_stages=list(state.completed_stages) if state else [],
        failed_stages=list(state.failed_stages) if state else [],
        blocked_stages=list(state.blocked_stages) if state else [],
        skipped_stages=list(state.skipped_stages) if state else [],
        stage_results=dict(state.stage_results) if state else {},
        artifacts=list(state.artifact_manifest) if state else [],
        task_usage=state.task_usage if state else 0,
        runtime_usage=state.runtime_usage if state else 0.0,
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
    )


def _stage_is_blocked(stage, state: OrchestratorState) -> tuple[bool, str]:
    failed_dependencies = [
        dependency
        for dependency in stage.dependencies
        if dependency in state.failed_stages or dependency in state.blocked_stages
    ]
    if failed_dependencies:
        return True, "Blocked by dependency failure: " + ", ".join(failed_dependencies)

    return False, ""


def _record_stage_result(
    state: OrchestratorState,
    stage_name: str,
    status: str,
    message: str,
    task_usage: int = 0,
    runtime_seconds: float = 0.0,
    artifacts: list[dict] | None = None,
    metadata: dict | None = None,
) -> None:
    artifacts = artifacts or []
    state.stage_results[stage_name] = {
        "status": status,
        "message": message,
        "task_usage": task_usage,
        "runtime_seconds": round(runtime_seconds, 6),
        "artifacts": artifacts,
        "metadata": metadata or {},
    }

    for artifact in artifacts:
        artifact.setdefault("created_at", _now())
        artifact.setdefault("config_hash", state.config_hash)
        if artifact not in state.artifact_manifest:
            state.artifact_manifest.append(artifact)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _mark_blocked_stage(
    state: OrchestratorState,
    stage,
    message: str,
) -> None:
    _append_unique(state.blocked_stages, stage.name)
    _record_stage_result(
        state,
        stage.name,
        STAGE_BLOCKED,
        message,
        task_usage=0,
        runtime_seconds=0.0,
        artifacts=[],
    )


def _remaining_runtime_exceeded(
    started_seconds: float,
    global_runtime_budget_seconds: float,
) -> bool:
    return (time.perf_counter() - started_seconds) > global_runtime_budget_seconds


def _execute_stage(context, stage, state: OrchestratorState) -> tuple[str, str]:
    if stage.runner is None:
        _append_unique(state.skipped_stages, stage.name)
        _record_stage_result(
            state,
            stage.name,
            STAGE_SKIPPED,
            "Stage has no runner",
        )
        return STAGE_SKIPPED, "Stage has no runner"

    stage_started = time.perf_counter()
    state.current_stage = stage.name
    state.touch()

    payload = stage.runner(context, stage, state)
    runtime_seconds = time.perf_counter() - stage_started
    task_usage = int(payload.get("task_usage", stage.task_budget or 1))
    artifacts = list(payload.get("artifacts", []))
    metadata = dict(payload.get("metadata", {}))
    message = str(payload.get("message", "Stage completed"))

    if stage.task_budget is not None and task_usage > stage.task_budget:
        raise RuntimeError(
            f"Stage task budget exceeded for {stage.name}: "
            f"{task_usage} > {stage.task_budget}"
        )

    if (
        stage.runtime_budget_seconds is not None
        and runtime_seconds > stage.runtime_budget_seconds
    ):
        raise RuntimeError(
            f"Stage runtime budget exceeded for {stage.name}: "
            f"{runtime_seconds:.6f} > {stage.runtime_budget_seconds}"
        )

    state.task_usage += task_usage
    state.runtime_usage += runtime_seconds
    _append_unique(state.completed_stages, stage.name)
    _record_stage_result(
        state,
        stage.name,
        STAGE_COMPLETED,
        message,
        task_usage=task_usage,
        runtime_seconds=runtime_seconds,
        artifacts=artifacts,
        metadata=metadata,
    )
    return STAGE_COMPLETED, message


def run_research_orchestrator(
    config_override: dict | None = None,
    registry: dict | None = None,
) -> OrchestratorResult:
    started_at = _now()
    started_seconds = time.perf_counter()
    context = build_orchestrator_context(config_override)

    if not context.enabled:
        return _make_result(
            context,
            plan=None,
            state=None,
            status="DISABLED",
            started_at=started_at,
            started_seconds=started_seconds,
            metadata={"reason": "Research orchestrator is disabled"},
        )

    adapter_mode = context.metadata.get("adapter_mode", "SMOKE")
    registry = registry or build_default_stage_registry(adapter_mode)
    plan = build_plan(context, registry)

    if context.dry_run:
        return _make_result(
            context,
            plan=plan,
            state=None,
            status="DRY_RUN",
            started_at=started_at,
            started_seconds=started_seconds,
            warnings=list(plan.warnings),
            metadata={"plan": summarize_plan(plan)},
        )

    context.run_directory().mkdir(parents=True, exist_ok=True)
    config_hash = calculate_config_hash(context.to_config_dict())
    state = None

    if context.resume_enabled and context.state_path().exists():
        state = load_state(context.state_path(), expected_config_hash=config_hash)
    else:
        state = OrchestratorState.create(context)

    state.status = "RUNNING"
    state.metadata["plan"] = summarize_plan(plan)
    save_state_atomic(state, context.state_path())

    errors = []

    for stage in plan.stages:
        if _remaining_runtime_exceeded(
            started_seconds,
            context.global_runtime_budget_seconds,
        ):
            _mark_blocked_stage(state, stage, "Global runtime budget exceeded")
            errors.append("Global runtime budget exceeded")
            save_state_atomic(state, context.state_path())
            break

        if state.task_usage >= context.global_task_budget:
            _mark_blocked_stage(state, stage, "Global task budget exhausted")
            errors.append("Global task budget exhausted")
            save_state_atomic(state, context.state_path())
            break

        blocked, blocked_message = _stage_is_blocked(stage, state)
        if blocked:
            _mark_blocked_stage(state, stage, blocked_message)
            save_state_atomic(state, context.state_path())
            if stage.required or context.fail_fast:
                break
            continue

        if (
            context.resume_enabled
            and stage.allow_resume
            and stage.name in state.completed_stages
            and validate_completed_stage_artifacts(
                state,
                stage.name,
                stage.metadata.get("contract_version"),
            )
        ):
            _append_unique(state.skipped_stages, stage.name)
            _record_stage_result(
                state,
                stage.name,
                STAGE_SKIPPED,
                "Resumed completed stage",
                metadata={"resume": True},
            )
            save_state_atomic(state, context.state_path())
            continue

        try:
            _execute_stage(context, stage, state)
        except Exception as error:
            runtime_seconds = time.perf_counter() - started_seconds
            message = str(error)
            errors.append(message)
            _append_unique(state.failed_stages, stage.name)
            _record_stage_result(
                state,
                stage.name,
                STAGE_FAILED,
                message,
                runtime_seconds=runtime_seconds,
                metadata={"traceback": traceback.format_exc()},
            )
            save_state_atomic(state, context.state_path())

            if context.fail_fast or (stage.required and not context.continue_on_stage_failure):
                break

        state.touch()
        save_state_atomic(state, context.state_path())

    state.current_stage = None
    if state.failed_stages or state.blocked_stages:
        state.status = "FAILED"
    else:
        state.status = "COMPLETED"
    state.touch()
    save_state_atomic(state, context.state_path())

    result = _make_result(
        context,
        plan=plan,
        state=state,
        status=state.status,
        started_at=started_at,
        started_seconds=started_seconds,
        warnings=list(plan.warnings),
        errors=errors,
        metadata={"plan": summarize_plan(plan)},
    )

    write_summary_report(result, str(context.summary_path()))
    write_artifact_manifest(result.artifacts, str(context.manifest_path()))
    write_stage_report(state, str(context.run_directory() / "orchestrator_stage_report.csv"))

    return result


def main() -> None:
    result = run_research_orchestrator()
    print(
        "Research orchestrator "
        f"{result.status}: {len(result.completed_stages)} completed, "
        f"{len(result.failed_stages)} failed, "
        f"{len(result.blocked_stages)} blocked"
    )


if __name__ == "__main__":
    main()
