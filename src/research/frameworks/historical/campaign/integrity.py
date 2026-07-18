from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.research.frameworks.historical.campaign.aggregation import enforce_structural_schema
from src.research.frameworks.historical.campaign.models import (
    CAMPAIGN_MANIFEST_VERSION,
    CAMPAIGN_PLAN_VERSION,
    HistoricalCampaignPlan,
    HistoricalCampaignTaskResult,
)
from src.research.frameworks.historical.campaign.planner import child_plan_for_task
from src.research.frameworks.historical.integrity import validate_historical_run
from src.research.frameworks.historical.storage import file_checksum, read_json
from src.research.run_management.run_identity import stable_identity_hash


class CampaignIntegrityError(RuntimeError):
    pass


def child_integrity_fingerprint(child_directory: str | Path) -> str:
    root = Path(child_directory)
    payload: dict[str, Any] = {}
    for name in ("plan.json", "manifest.json", "merge_manifest.json"):
        path = root / name
        if not path.is_file():
            raise CampaignIntegrityError(f"child run file missing: {path}")
        payload[name] = file_checksum(path)
    checkpoints = sorted(root.glob("chunks/chunk_*/checkpoint.json"))
    if not checkpoints:
        raise CampaignIntegrityError(f"child run has no checkpoints: {root}")
    payload["checkpoints"] = {path.parent.name: file_checksum(path) for path in checkpoints}
    return stable_identity_hash(payload)


def validate_campaign(
    campaign_directory: str | Path,
    plan: HistoricalCampaignPlan,
    source_sets: Mapping[str, object],
    strict: bool = True,
) -> dict[str, Any]:
    root = Path(campaign_directory)
    errors = []
    plan_path = root / "campaign_plan.json"
    manifest_path = root / "campaign_manifest.json"
    if not plan_path.is_file():
        errors.append("campaign_plan_missing")
        stored_plan = {}
    else:
        try:
            stored_plan = read_json(plan_path)
        except Exception:
            errors.append("campaign_plan_unreadable")
            stored_plan = {}
    if stored_plan.get("plan_version") != CAMPAIGN_PLAN_VERSION:
        errors.append("campaign_plan_version")
    for field in ("campaign_id", "configuration_fingerprint", "code_fingerprint", "plan_fingerprint"):
        if stored_plan.get(field) != getattr(plan, field):
            errors.append(f"campaign_plan_{field}")
    expected_order = [task.task_id for task in plan.tasks]
    if stored_plan.get("task_ordering") != expected_order:
        errors.append("campaign_task_ordering")
    if len(expected_order) != len(set(expected_order)):
        errors.append("campaign_duplicate_task_ids")
    if not manifest_path.is_file():
        errors.append("campaign_manifest_missing")
        manifest = {}
    else:
        try:
            manifest = read_json(manifest_path)
        except Exception:
            errors.append("campaign_manifest_unreadable")
            manifest = {}
    if manifest.get("manifest_schema_version") != CAMPAIGN_MANIFEST_VERSION:
        errors.append("campaign_manifest_version")
    for field in ("campaign_id", "configuration_fingerprint", "code_fingerprint", "plan_fingerprint"):
        if manifest.get(field) != getattr(plan, field):
            errors.append(f"campaign_manifest_{field}")
    if manifest.get("task_ordering") != expected_order:
        errors.append("campaign_manifest_task_ordering")
    try:
        enforce_structural_schema(manifest)
    except ValueError as error:
        errors.append(str(error))
    task_validation = {}
    for task in plan.tasks:
        result_path = root / "task_results" / f"{task.task_id}.json"
        if not result_path.is_file():
            task_validation[task.task_id] = {"valid": False, "errors": ["task_result_missing"]}
            continue
        try:
            result = HistoricalCampaignTaskResult.from_dict(read_json(result_path))
            if result.task_id != task.task_id or result.child_run_id != task.child_run_id:
                raise CampaignIntegrityError("task result identity mismatch")
            enforce_structural_schema(result.to_dict())
            binding = source_sets[task.source_set_name]
            child_plan = child_plan_for_task(plan, task, binding)
            child_directory = root / "children" / task.child_run_id
            child_validation = validate_historical_run(child_directory, child_plan, strict=True)
            expected_fingerprint = child_integrity_fingerprint(child_directory)
            if result.child_integrity_fingerprint != expected_fingerprint:
                raise CampaignIntegrityError("child integrity fingerprint mismatch")
            task_validation[task.task_id] = {"valid": bool(child_validation["valid"]), "errors": []}
        except Exception as error:
            task_validation[task.task_id] = {"valid": False, "errors": [f"{type(error).__name__}: {error}"]}
    aggregate_manifest = root / "summaries" / "structural_summary_manifest.json"
    if aggregate_manifest.is_file():
        try:
            aggregate = read_json(aggregate_manifest)
            enforce_structural_schema(aggregate)
            if aggregate.get("campaign_id") != plan.campaign_id:
                errors.append("aggregate_campaign_id")
            if manifest.get("aggregate_fingerprint") != aggregate.get("aggregate_fingerprint"):
                errors.append("aggregate_fingerprint")
        except Exception as error:
            errors.append(f"aggregate_unreadable:{error}")
    elif manifest.get("status") == "completed":
        errors.append("aggregate_missing")
    invalid_tasks = [task_id for task_id, value in task_validation.items() if not value["valid"]]
    valid = not errors and not invalid_tasks
    result = {"valid": valid, "errors": errors, "invalid_tasks": invalid_tasks, "tasks": task_validation}
    if strict and not valid:
        raise CampaignIntegrityError(
            f"campaign {plan.campaign_id} failed integrity: {', '.join(errors + invalid_tasks)}"
        )
    return result
