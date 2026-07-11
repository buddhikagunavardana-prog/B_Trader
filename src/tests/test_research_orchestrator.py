from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.orchestrator.orchestrator_context import (
    build_orchestrator_context,
    load_orchestrator_config,
)
from src.research.orchestrator.orchestrator_plan import (
    build_plan,
    summarize_plan,
)
from src.research.orchestrator.orchestrator_registry import (
    build_default_stage_registry,
    get_stage,
)
from src.research.orchestrator.orchestrator_report import (
    build_stage_report,
)
from src.research.orchestrator.orchestrator_runner import (
    run_research_orchestrator,
)
from src.research.orchestrator.orchestrator_stage import OrchestratorStage
from src.research.orchestrator.orchestrator_state import (
    OrchestratorState,
    calculate_config_hash,
    load_state,
    save_state_atomic,
    validate_completed_stage_artifacts,
)


def _base_override(directory: str, **updates) -> dict:
    config = {
        "enabled": True,
        "run_id": "unit_run",
        "dry_run": False,
        "resume_enabled": True,
        "fail_fast": True,
        "continue_on_stage_failure": False,
        "global_task_budget": 100,
        "global_runtime_budget_seconds": 60,
        "output_directory": directory,
        "state_file": "state.json",
        "summary_file": "summary.json",
        "manifest_file": "manifest.json",
        "smoke_mode": False,
        "enabled_stages": ["alpha"],
        "stage_order": ["alpha", "beta", "gamma"],
        "stage_overrides": {},
    }
    config.update(updates)
    return config


def _artifact(path: Path, stage_name: str) -> dict:
    return {
        "name": f"{stage_name}_artifact",
        "artifact_type": "JSON",
        "path": str(path),
        "producer_stage": stage_name,
        "schema_version": "1",
        "required": True,
        "status": "CREATED",
        "metadata": {},
    }


def _success_runner(context, stage, state):
    output_path = context.run_directory() / f"{stage.name}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"ok": true}', encoding="utf-8")
    return {
        "message": f"{stage.name} completed",
        "task_usage": 1,
        "artifacts": [_artifact(output_path, stage.name)],
        "metadata": {"stage": stage.name},
    }


def _failure_runner(context, stage, state):
    raise RuntimeError(f"{stage.name} failed")


def _registry(
    alpha_runner=_success_runner,
    beta_runner=_success_runner,
    gamma_runner=_success_runner,
) -> dict:
    return {
        "alpha": OrchestratorStage(
            name="alpha",
            display_name="Alpha",
            runner=alpha_runner,
            task_budget=1,
        ),
        "beta": OrchestratorStage(
            name="beta",
            display_name="Beta",
            dependencies=["alpha"],
            runner=beta_runner,
            task_budget=1,
        ),
        "gamma": OrchestratorStage(
            name="gamma",
            display_name="Gamma",
            dependencies=["beta"],
            runner=gamma_runner,
            task_budget=1,
        ),
    }


def test_config_loading_and_disabled_behavior():
    config = load_orchestrator_config()
    result = run_research_orchestrator({"enabled": False})

    assert config["enabled"] is False
    assert result.status == "DISABLED"
    assert result.completed_stages == []


def test_stage_registration_and_unknown_stage_error():
    registry = build_default_stage_registry()

    assert "optimization_search" in registry
    assert get_stage("load_data", registry).name == "load_data"

    try:
        get_stage("missing", registry)
    except ValueError as error:
        assert "Unknown orchestrator stage" in str(error)
    else:
        raise AssertionError("Unknown stage did not fail")


def test_dry_run_builds_plan_without_execution():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(directory, dry_run=True, enabled_stages=["gamma"]),
            registry=_registry(),
        )

        assert result.status == "DRY_RUN"
        assert result.planned_stages == ["alpha", "beta", "gamma"]
        assert not Path(directory, "unit_run").exists()


def test_dependency_chain_and_deterministic_order():
    with TemporaryDirectory() as directory:
        context = build_orchestrator_context(
            _base_override(directory, dry_run=True, enabled_stages=["gamma"])
        )
        plan = build_plan(context, _registry())
        summary = summarize_plan(plan)

        assert plan.execution_order == ["alpha", "beta", "gamma"]
        assert summary["stage_count"] == 3


def test_cycle_detection():
    with TemporaryDirectory() as directory:
        context = build_orchestrator_context(
            _base_override(directory, enabled_stages=["alpha", "beta"])
        )
        registry = {
            "alpha": OrchestratorStage(
                name="alpha",
                display_name="Alpha",
                dependencies=["beta"],
                runner=_success_runner,
            ),
            "beta": OrchestratorStage(
                name="beta",
                display_name="Beta",
                dependencies=["alpha"],
                runner=_success_runner,
            ),
        }

        try:
            build_plan(context, registry)
        except ValueError as error:
            assert "Cycle detected" in str(error)
        else:
            raise AssertionError("Cycle did not fail")


def test_required_execution_and_artifact_manifest():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(directory, enabled_stages=["beta"]),
            registry=_registry(),
        )

        manifest_path = Path(directory, "unit_run", "manifest.json")
        summary_path = Path(directory, "unit_run", "summary.json")
        stage_report_path = Path(directory, "unit_run", "orchestrator_stage_report.csv")

        assert result.status == "COMPLETED"
        assert result.completed_stages == ["alpha", "beta"]
        assert len(result.artifacts) == 2
        assert "created_at" in result.artifacts[0]
        assert "config_hash" in result.artifacts[0]
        assert manifest_path.exists()
        assert summary_path.exists()
        assert stage_report_path.exists()


def test_failure_blocks_dependent_stage():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(
                directory,
                enabled_stages=["beta"],
                fail_fast=False,
                continue_on_stage_failure=True,
            ),
            registry=_registry(alpha_runner=_failure_runner),
        )

        assert result.status == "FAILED"
        assert result.failed_stages == ["alpha"]
        assert result.blocked_stages == ["beta"]


def test_independent_stage_continues_when_policy_allows():
    with TemporaryDirectory() as directory:
        registry = {
            "alpha": OrchestratorStage(
                name="alpha",
                display_name="Alpha",
                required=False,
                runner=_failure_runner,
            ),
            "beta": OrchestratorStage(
                name="beta",
                display_name="Beta",
                runner=_success_runner,
            ),
        }
        result = run_research_orchestrator(
            _base_override(
                directory,
                enabled_stages=["alpha", "beta"],
                stage_order=["alpha", "beta"],
                fail_fast=False,
                continue_on_stage_failure=True,
            ),
            registry=registry,
        )

        assert result.status == "FAILED"
        assert result.failed_stages == ["alpha"]
        assert result.completed_stages == ["beta"]


def test_fail_fast_stops_after_first_failure():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(
                directory,
                enabled_stages=["alpha", "beta"],
                stage_order=["alpha", "beta"],
                fail_fast=True,
                continue_on_stage_failure=True,
            ),
            registry=_registry(alpha_runner=_failure_runner),
        )

        assert result.failed_stages == ["alpha"]
        assert result.blocked_stages == []
        assert "beta" not in result.completed_stages


def test_global_task_budget_validation():
    with TemporaryDirectory() as directory:
        try:
            run_research_orchestrator(
                _base_override(
                    directory,
                    enabled_stages=["beta"],
                    global_task_budget=1,
                ),
                registry=_registry(),
            )
        except ValueError as error:
            assert "global task budget" in str(error)
        else:
            raise AssertionError("Budget overflow did not fail")


def test_stage_task_budget_validation():
    def expensive_runner(context, stage, state):
        return {
            "message": "too much",
            "task_usage": 3,
            "artifacts": [],
        }

    with TemporaryDirectory() as directory:
        registry = {
            "alpha": OrchestratorStage(
                name="alpha",
                display_name="Alpha",
                runner=expensive_runner,
                task_budget=1,
            )
        }
        result = run_research_orchestrator(
            _base_override(directory, enabled_stages=["alpha"]),
            registry=registry,
        )

        assert result.status == "FAILED"
        assert "Stage task budget exceeded" in result.errors[0]


def test_global_runtime_budget_handling():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(
                directory,
                enabled_stages=["alpha"],
                global_runtime_budget_seconds=-1,
            ),
            registry=_registry(),
        )

        assert result.status == "FAILED"
        assert result.blocked_stages == ["alpha"]
        assert "runtime budget" in result.errors[0]


def test_state_creation_atomic_load_and_hash_validation():
    with TemporaryDirectory() as directory:
        context = build_orchestrator_context(_base_override(directory))
        state = OrchestratorState.create(context)
        state_path = Path(directory, "state.json")
        save_state_atomic(state, state_path)

        loaded = load_state(state_path, expected_config_hash=state.config_hash)

        assert loaded.run_id == "unit_run"
        assert calculate_config_hash({"b": 2, "a": 1}) == calculate_config_hash({
            "a": 1,
            "b": 2,
        })

        try:
            load_state(state_path, expected_config_hash="wrong")
        except ValueError as error:
            assert "config hash" in str(error)
        else:
            raise AssertionError("Bad config hash did not fail")


def test_resume_completed_stage_and_missing_artifact_invalidation():
    with TemporaryDirectory() as directory:
        override = _base_override(directory, enabled_stages=["alpha"])
        first = run_research_orchestrator(override, registry=_registry())
        second = run_research_orchestrator(override, registry=_registry())
        artifact_path = Path(first.artifacts[0]["path"])
        artifact_path.unlink()
        state = load_state(Path(directory, "unit_run", "state.json"))

        assert first.status == "COMPLETED"
        assert second.skipped_stages == ["alpha"]
        assert validate_completed_stage_artifacts(state, "alpha") is False


def test_incompatible_state_version_rejected():
    with TemporaryDirectory() as directory:
        state_path = Path(directory, "bad_state.json")
        state_path.write_text(
            '{"orchestrator_version":"old","run_id":"x","config_hash":"h",'
            '"created_at":"x","updated_at":"x"}',
            encoding="utf-8",
        )

        try:
            load_state(state_path)
        except ValueError as error:
            assert "version" in str(error)
        else:
            raise AssertionError("Old state version did not fail")


def test_result_serialization_and_report_schema():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator(
            _base_override(directory, enabled_stages=["alpha"]),
            registry=_registry(),
        )
        state = load_state(Path(directory, "unit_run", "state.json"))
        report = build_stage_report(state)
        payload = result.to_dict()

        assert payload["status"] == "COMPLETED"
        assert list(report.columns) == [
            "Stage",
            "Status",
            "Message",
            "Task Usage",
            "Runtime Seconds",
            "Artifact Count",
        ]


def test_smoke_mode_limits_default_plan_to_three_stages():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator({
            "enabled": True,
            "run_id": "smoke_unit",
            "dry_run": True,
            "output_directory": directory,
            "smoke_mode": True,
            "enabled_stages": [],
        })

        assert result.status == "DRY_RUN"
        assert len(result.planned_stages) <= 3


def test_disabled_default_preserves_backward_compatibility():
    result = run_research_orchestrator()

    assert result.status == "DISABLED"
    assert result.task_usage == 0


def test_small_smoke_execution_uses_bounded_stages_only():
    with TemporaryDirectory() as directory:
        result = run_research_orchestrator({
            "enabled": True,
            "run_id": "small_smoke",
            "dry_run": False,
            "resume_enabled": False,
            "fail_fast": True,
            "continue_on_stage_failure": False,
            "global_task_budget": 20,
            "global_runtime_budget_seconds": 60,
            "output_directory": directory,
            "smoke_mode": True,
            "enabled_stages": ["load_data", "optimization_search", "monte_carlo"],
        })

        assert result.status == "COMPLETED"
        assert result.completed_stages == [
            "load_data",
            "optimization_search",
            "monte_carlo",
        ]
        assert result.task_usage <= 20


if __name__ == "__main__":
    test_config_loading_and_disabled_behavior()
    test_stage_registration_and_unknown_stage_error()
    test_dry_run_builds_plan_without_execution()
    test_dependency_chain_and_deterministic_order()
    test_cycle_detection()
    test_required_execution_and_artifact_manifest()
    test_failure_blocks_dependent_stage()
    test_independent_stage_continues_when_policy_allows()
    test_fail_fast_stops_after_first_failure()
    test_global_task_budget_validation()
    test_stage_task_budget_validation()
    test_global_runtime_budget_handling()
    test_state_creation_atomic_load_and_hash_validation()
    test_resume_completed_stage_and_missing_artifact_invalidation()
    test_incompatible_state_version_rejected()
    test_result_serialization_and_report_schema()
    test_smoke_mode_limits_default_plan_to_three_stages()
    test_disabled_default_preserves_backward_compatibility()
    test_small_smoke_execution_uses_bounded_stages_only()
    print("test_research_orchestrator passed")
