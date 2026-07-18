from __future__ import annotations

from pathlib import Path
from typing import Mapping

from src.research.frameworks.historical.campaign.integrity import child_integrity_fingerprint
from src.research.frameworks.historical.campaign.models import CampaignRecoveryReport, HistoricalCampaignPlan
from src.research.frameworks.historical.campaign.planner import child_plan_for_task
from src.research.frameworks.historical.integrity import validate_historical_run
from src.research.frameworks.historical.storage import read_json


def recover_historical_campaign(
    campaign_directory: str | Path,
    plan: HistoricalCampaignPlan,
    source_sets: Mapping[str, object],
) -> CampaignRecoveryReport:
    root = Path(campaign_directory)
    retained = []
    reused = []
    resumed = []
    invalidated = []
    rerun = []
    orphans = []
    corrupt = []
    incompatible = []
    retained_children = []
    for temporary in root.rglob("*.tmp") if root.exists() else ():
        orphans.append(str(temporary.relative_to(root)))
    expected_children = {task.child_run_id for task in plan.tasks}
    children_root = root / "children"
    if children_root.is_dir():
        for directory in children_root.iterdir():
            if directory.is_dir() and directory.name not in expected_children:
                orphans.append(str(directory.relative_to(root)))
    for task in plan.tasks:
        child = children_root / task.child_run_id
        result = root / "task_results" / f"{task.task_id}.json"
        if not child.exists():
            rerun.append(task.task_id)
            if result.exists():
                invalidated.append(task.task_id)
            continue
        try:
            child_plan = child_plan_for_task(plan, task, source_sets[task.source_set_name])
            validation = validate_historical_run(child, child_plan, strict=True)
            child_integrity_fingerprint(child)
            if not validation["valid"]:
                raise ValueError("child validation returned invalid")
            retained.append(task.task_id)
            retained_children.append(task.child_run_id)
            if result.exists():
                reused.append(task.task_id)
            else:
                resumed.append(task.task_id)
        except (KeyError, ValueError) as error:
            incompatible.append(f"{task.task_id}:{error}")
            invalidated.append(task.task_id)
            rerun.append(task.task_id)
        except Exception as error:
            corrupt.append(f"{task.task_id}:{type(error).__name__}:{error}")
            invalidated.append(task.task_id)
            rerun.append(task.task_id)
    stale = []
    aggregate_path = root / "summaries" / "structural_summary_manifest.json"
    manifest_path = root / "campaign_manifest.json"
    if aggregate_path.exists():
        try:
            aggregate = read_json(aggregate_path)
            manifest = read_json(manifest_path)
            if aggregate.get("aggregate_fingerprint") != manifest.get("aggregate_fingerprint"):
                stale.append(str(aggregate_path.relative_to(root)))
        except Exception:
            stale.append(str(aggregate_path.relative_to(root)))
    elif manifest_path.exists():
        try:
            if read_json(manifest_path).get("aggregate_fingerprint"):
                stale.append("summaries/structural_summary_manifest.json")
        except Exception:
            corrupt.append("campaign_manifest.json")
    return CampaignRecoveryReport(
        plan.campaign_id,
        tuple(retained),
        tuple(reused),
        tuple(resumed),
        tuple(invalidated),
        tuple(rerun),
        tuple(sorted(orphans)),
        tuple(corrupt),
        tuple(incompatible),
        tuple(stale),
        tuple(retained_children),
    )


def resume_historical_campaign(plan, source_sets, cancellation_control=None):
    from src.research.frameworks.historical.campaign.orchestrator import run_historical_campaign
    return run_historical_campaign(plan, source_sets, cancellation_control=cancellation_control)
