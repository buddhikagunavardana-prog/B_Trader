from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from src.research.frameworks.historical.campaign.aggregation import (
    aggregate_campaign_results,
    write_campaign_aggregate,
)
from src.research.frameworks.historical.campaign.integrity import (
    CampaignIntegrityError,
    child_integrity_fingerprint,
    validate_campaign,
)
from src.research.frameworks.historical.campaign.models import (
    CampaignFailurePolicy,
    CampaignStatus,
    CampaignTaskStatus,
    HistoricalCampaignManifest,
    HistoricalCampaignPlan,
    HistoricalCampaignResult,
    HistoricalCampaignTaskResult,
    safe_campaign_directory,
)
from src.research.frameworks.historical.campaign.planner import child_plan_for_task
from src.research.frameworks.historical.checkpoints import load_checkpoint
from src.research.frameworks.historical.exceptions import HistoricalCancellationError
from src.research.frameworks.historical.integrity import validate_historical_run
from src.research.frameworks.historical.locking import ChunkLock
from src.research.frameworks.historical.merge import merge_historical_artifacts
from src.research.frameworks.historical.models import RunStatus
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.recovery import resume_historical_research
from src.research.frameworks.historical.storage import atomic_json, read_decision_artifact, read_json


class CampaignControl:
    def __init__(self, cancel_path: str | Path | None = None, pause_path: str | Path | None = None):
        self.cancel_path = None if cancel_path is None else Path(cancel_path)
        self.pause_path = None if pause_path is None else Path(pause_path)
        self._cancelled = False
        self._paused = False

    def cancel(self) -> None:
        self._cancelled = True
        if self.cancel_path is not None:
            self.cancel_path.parent.mkdir(parents=True, exist_ok=True)
            self.cancel_path.write_text("cancelled\n", encoding="utf-8")

    def pause(self) -> None:
        self._paused = True
        if self.pause_path is not None:
            self.pause_path.parent.mkdir(parents=True, exist_ok=True)
            self.pause_path.write_text("paused\n", encoding="utf-8")

    @property
    def cancelled(self) -> bool:
        return self._cancelled or bool(self.cancel_path and self.cancel_path.exists())

    @property
    def paused(self) -> bool:
        return self._paused or bool(self.pause_path and self.pause_path.exists())

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise HistoricalCancellationError("historical campaign cancelled at a safe boundary")


def _manifest(
    plan: HistoricalCampaignPlan,
    status: CampaignStatus,
    results: Mapping[str, HistoricalCampaignTaskResult],
    attempts: Mapping[str, int],
    aggregate=None,
    warnings=(),
    cancellation_state="active",
    recovery_state="clean",
    timing=None,
) -> HistoricalCampaignManifest:
    statuses = {task.task_id: CampaignTaskStatus.PLANNED.value for task in plan.tasks}
    statuses.update({task_id: result.status.value for task_id, result in results.items()})
    child_ids = {task.task_id: task.child_run_id for task in plan.tasks}
    completed = [result for result in results.values() if result.status in {CampaignTaskStatus.COMPLETED, CampaignTaskStatus.REUSED}]
    memory = {
        "maximum_child_input_bytes": max(
            (int(result.memory_diagnostics.get("maximum_input_bytes", 0)) for result in completed),
            default=0,
        ),
        "active_child_limit": 1,
    }
    return HistoricalCampaignManifest(
        campaign_id=plan.campaign_id,
        status=status,
        configuration_fingerprint=plan.configuration_fingerprint,
        code_fingerprint=plan.code_fingerprint,
        plan_fingerprint=plan.plan_fingerprint,
        task_ordering=tuple(task.task_id for task in plan.tasks),
        source_set_fingerprints=dict(plan.source_set_fingerprints),
        task_statuses=statuses,
        task_attempts=dict(attempts),
        task_results={task_id: result.to_dict() for task_id, result in results.items()},
        child_run_ids=child_ids,
        child_integrity_fingerprints={
            task_id: result.child_integrity_fingerprint for task_id, result in results.items()
            if result.child_integrity_fingerprint
        },
        aggregate_fingerprint="" if aggregate is None else aggregate.aggregate_fingerprint,
        warnings=tuple(warnings),
        structural_counts={
            "total_tasks": len(plan.tasks),
            "completed_tasks": len(completed),
            "reused_tasks": sum(result.status is CampaignTaskStatus.REUSED for result in results.values()),
            "failed_tasks": sum(result.status is CampaignTaskStatus.FAILED for result in results.values()),
        },
        cancellation_state=cancellation_state,
        recovery_state=recovery_state,
        timing_diagnostics=dict(timing or {}),
        memory_diagnostics=memory,
    )


def _write_manifest(root: Path, manifest: HistoricalCampaignManifest) -> None:
    payload = manifest.to_dict()
    atomic_json(root / "campaign_manifest.json", payload)
    atomic_json(root / "campaign_status.json", {
        "campaign_id": manifest.campaign_id,
        "status": manifest.status.value,
        "task_statuses": dict(manifest.task_statuses),
        "cancellation_state": manifest.cancellation_state,
        "recovery_state": manifest.recovery_state,
    })


def _task_result_path(root: Path, task_id: str) -> Path:
    if not task_id or any(part in task_id for part in ("..", "/", "\\")):
        raise ValueError("unsafe campaign task ID")
    target = (root / "task_results" / f"{task_id}.json").resolve()
    if root.resolve() not in target.parents:
        raise ValueError("campaign task result path escapes campaign root")
    return target


def _structural_child_result(task, child_plan, child_result, merged, attempt: int, status) -> HistoricalCampaignTaskResult:
    direction_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    valid_rows = skipped_rows = warnings = 0
    maximum_input = maximum_output = 0
    timing: Counter[str] = Counter()
    lifecycle_columns = ("controller_state_after", "lifecycle_state", "position_state_after")
    for chunk in child_plan.chunks:
        checkpoint = load_checkpoint(Path(child_result.run_directory) / "chunks" / f"chunk_{chunk.chunk_index:06d}" / "checkpoint.json")
        artifact = Path(child_result.run_directory) / "chunks" / f"chunk_{chunk.chunk_index:06d}" / checkpoint.output_artifact
        frame = read_decision_artifact(artifact, child_plan.config.artifact_format)
        if "decision_valid" in frame:
            valid = frame["decision_valid"].fillna(False).astype(bool)
            valid_rows += int(valid.sum())
            skipped_rows += int((~valid).sum())
        else:
            valid_rows += len(frame)
        if "direction" in frame:
            direction_counts.update(str(value) for value in frame["direction"].fillna("missing"))
        for column in lifecycle_columns:
            if column in frame:
                lifecycle_counts.update(str(value) for value in frame[column].fillna("missing"))
                break
        warnings += len(checkpoint.warnings)
        maximum_input = max(maximum_input, int(checkpoint.memory_summary.get("input_bytes", 0)))
        maximum_output = max(maximum_output, int(checkpoint.memory_summary.get("output_bytes", 0)))
        for name, value in checkpoint.timing_summary.items():
            if isinstance(value, (int, float)):
                timing[name] += float(value)
        del frame
    integrity = child_integrity_fingerprint(child_result.run_directory)
    return HistoricalCampaignTaskResult(
        task_id=task.task_id,
        child_run_id=task.child_run_id,
        status=status,
        attempt_number=attempt,
        child_run_directory=str(child_result.run_directory),
        child_integrity_fingerprint=integrity,
        child_schema_fingerprint=merged.schema_fingerprint,
        logical_row_count=merged.row_count,
        chunk_count=len(child_plan.chunks),
        valid_row_count=valid_rows,
        skipped_row_count=skipped_rows,
        decision_direction_counts=dict(sorted(direction_counts.items())),
        lifecycle_state_counts=dict(sorted(lifecycle_counts.items())),
        warning_count=warnings,
        validation_count=len(child_plan.chunks) + 1,
        memory_diagnostics={"maximum_input_bytes": maximum_input, "maximum_output_bytes": maximum_output},
        timing_diagnostics=dict(sorted(timing.items())),
    )


def _reusable_result(root, plan, task, binding):
    path = _task_result_path(root, task.task_id)
    if not path.is_file():
        return None
    try:
        result = HistoricalCampaignTaskResult.from_dict(read_json(path))
        child_plan = child_plan_for_task(plan, task, binding)
        child_directory = root / "children" / task.child_run_id
        validation = validate_historical_run(child_directory, child_plan, strict=True)
        if not validation["valid"] or result.child_integrity_fingerprint != child_integrity_fingerprint(child_directory):
            return None
        return replace(result, status=CampaignTaskStatus.REUSED)
    except Exception:
        return None


def run_historical_campaign(
    plan: HistoricalCampaignPlan,
    source_sets: Mapping[str, object],
    cancellation_control: CampaignControl | None = None,
    stale_lock_timeout_seconds: int = 300,
    stop_after_tasks: int | None = None,
    pause_after_tasks: int | None = None,
) -> HistoricalCampaignResult:
    if plan.config.concurrency != 1:
        raise ValueError("Phase 24.9 campaign execution requires concurrency exactly 1")
    if set(source_sets) != set(plan.source_set_fingerprints):
        raise ValueError("runtime campaign source sets differ from the deterministic plan")
    for name, fingerprint in plan.source_set_fingerprints.items():
        if source_sets[name].fingerprint != fingerprint:
            raise ValueError(f"runtime source-set fingerprint changed: {name}")
    control = cancellation_control or CampaignControl()
    root = safe_campaign_directory(plan.config.output_root, plan.campaign_id)
    root.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    with ChunkLock(root / "campaign.lock", stale_timeout_seconds=stale_lock_timeout_seconds):
        plan_path = root / "campaign_plan.json"
        payload = plan.to_dict()
        if plan_path.exists() and read_json(plan_path) != payload:
            raise CampaignIntegrityError(f"campaign {plan.campaign_id} stored plan differs from deterministic plan")
        if not plan_path.exists():
            atomic_json(plan_path, payload)
        results: dict[str, HistoricalCampaignTaskResult] = {}
        attempts: dict[str, int] = {}
        existing_manifest = root / "campaign_manifest.json"
        if existing_manifest.exists():
            stored = read_json(existing_manifest)
            for task_id, raw in stored.get("task_results", {}).items():
                try:
                    results[task_id] = HistoricalCampaignTaskResult.from_dict(raw)
                except Exception:
                    continue
            attempts.update({str(key): int(value) for key, value in stored.get("task_attempts", {}).items()})
        _write_manifest(root, _manifest(plan, CampaignStatus.RUNNING, results, attempts))
        failures = []
        for index, task in enumerate(plan.tasks):
            if stop_after_tasks is not None and index >= stop_after_tasks:
                control.cancel()
            if pause_after_tasks is not None and index >= pause_after_tasks:
                control.pause()
            if control.cancelled or control.paused:
                status = CampaignStatus.CANCELLED if control.cancelled else CampaignStatus.PAUSED
                state = "cancelled" if control.cancelled else "paused"
                manifest = _manifest(plan, status, results, attempts, cancellation_state=state)
                _write_manifest(root, manifest)
                return HistoricalCampaignResult(plan.campaign_id, status, str(root), len(results), len(plan.tasks), sum(r.status is CampaignTaskStatus.REUSED for r in results.values()), None)
            binding = source_sets[task.source_set_name]
            reusable = _reusable_result(root, plan, task, binding)
            if reusable is not None:
                results[task.task_id] = reusable
                atomic_json(_task_result_path(root, task.task_id), reusable.to_dict())
                _write_manifest(root, _manifest(plan, CampaignStatus.RUNNING, results, attempts, recovery_state="reused"))
                continue
            attempt = attempts.get(task.task_id, 0) + 1
            attempts[task.task_id] = attempt
            try:
                child_plan = child_plan_for_task(plan, task, binding)
                child_directory = root / "children" / task.child_run_id
                if (child_directory / "plan.json").exists():
                    try:
                        validation = validate_historical_run(child_directory, child_plan, strict=True)
                        if not validation["valid"]:
                            raise CampaignIntegrityError("child run is invalid")
                        child_result = type("ChildResult", (), {
                            "run_directory": str(child_directory),
                            "status": RunStatus.COMPLETED,
                        })()
                    except Exception:
                        child_result = resume_historical_research(child_directory, binding.sources, cancellation_token=control)
                else:
                    child_result = run_historical_research(child_plan, binding.sources, cancellation_token=control)
                if child_result.status is not RunStatus.COMPLETED:
                    status = CampaignStatus.CANCELLED if child_result.status is RunStatus.CANCELLED else CampaignStatus.RECOVERABLE
                    _write_manifest(root, _manifest(plan, status, results, attempts, cancellation_state=status.value))
                    return HistoricalCampaignResult(plan.campaign_id, status, str(root), len(results), len(plan.tasks), sum(r.status is CampaignTaskStatus.REUSED for r in results.values()), None)
                child_validation = validate_historical_run(child_result.run_directory, child_plan, strict=True)
                if not child_validation["valid"]:
                    raise CampaignIntegrityError(f"child run {task.child_run_id} failed validation")
                merged = merge_historical_artifacts(child_result.run_directory)
                task_result = _structural_child_result(
                    task, child_plan, child_result, merged, attempt, CampaignTaskStatus.COMPLETED
                )
                results[task.task_id] = task_result
                atomic_json(_task_result_path(root, task.task_id), task_result.to_dict())
                _write_manifest(root, _manifest(plan, CampaignStatus.RUNNING, results, attempts))
            except HistoricalCancellationError:
                manifest = _manifest(plan, CampaignStatus.CANCELLED, results, attempts, cancellation_state="cancelled")
                _write_manifest(root, manifest)
                return HistoricalCampaignResult(plan.campaign_id, CampaignStatus.CANCELLED, str(root), len(results), len(plan.tasks), sum(r.status is CampaignTaskStatus.REUSED for r in results.values()), None)
            except Exception as error:
                failures.append(f"{task.task_id}:{type(error).__name__}:{error}")
                failed = HistoricalCampaignTaskResult(
                    task.task_id, task.child_run_id, CampaignTaskStatus.FAILED, attempt,
                    str(root / "children" / task.child_run_id), "", "", 0, task.child_chunk_count,
                    0, 0, errors=(f"{type(error).__name__}: {error}",),
                )
                results[task.task_id] = failed
                atomic_json(_task_result_path(root, task.task_id), failed.to_dict())
                _write_manifest(root, _manifest(plan, CampaignStatus.RUNNING, results, attempts, warnings=failures, recovery_state="task_failure"))
                if plan.config.failure_policy is CampaignFailurePolicy.FAIL_FAST:
                    final = _manifest(plan, CampaignStatus.FAILED, results, attempts, warnings=failures, recovery_state="recoverable")
                    _write_manifest(root, final)
                    raise
            if control.cancelled or control.paused:
                status = CampaignStatus.CANCELLED if control.cancelled else CampaignStatus.PAUSED
                _write_manifest(root, _manifest(plan, status, results, attempts, cancellation_state=status.value))
                return HistoricalCampaignResult(plan.campaign_id, status, str(root), len(results), len(plan.tasks), sum(r.status is CampaignTaskStatus.REUSED for r in results.values()), None)
        if control.cancelled or control.paused:
            status = CampaignStatus.CANCELLED if control.cancelled else CampaignStatus.PAUSED
            _write_manifest(root, _manifest(plan, status, results, attempts, cancellation_state=status.value))
            return HistoricalCampaignResult(plan.campaign_id, status, str(root), len(results), len(plan.tasks), sum(r.status is CampaignTaskStatus.REUSED for r in results.values()), None)
        aggregate = aggregate_campaign_results(plan, results.values())
        write_campaign_aggregate(root, aggregate)
        final_status = CampaignStatus.FAILED if failures else CampaignStatus.COMPLETED
        elapsed = perf_counter() - started
        final_manifest = _manifest(
            plan, final_status, results, attempts, aggregate=aggregate, warnings=failures,
            recovery_state="clean" if not failures else "recoverable",
            timing={"elapsed_seconds": elapsed, "diagnostic_only": True},
        )
        _write_manifest(root, final_manifest)
        validation = validate_campaign(root, plan, source_sets, strict=not failures)
        atomic_json(root / "campaign_integrity.json", validation)
        return HistoricalCampaignResult(
            plan.campaign_id,
            final_status,
            str(root),
            aggregate.completed_task_count,
            len(plan.tasks),
            aggregate.reused_task_count,
            aggregate,
            tuple(failures),
        )
