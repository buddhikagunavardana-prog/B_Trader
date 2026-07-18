from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.research.frameworks.historical.campaign.models import (
    HistoricalCampaignAggregate,
    HistoricalCampaignPlan,
    HistoricalCampaignTaskResult,
)
from src.research.frameworks.historical.storage import atomic_json
from src.research.run_management.run_identity import stable_identity_hash


PROHIBITED_FIELD_TERMS = {
    "pnl", "roi", "return", "profit", "loss_amount", "win_rate", "profit_factor",
    "drawdown", "sharpe", "expectancy", "balance", "equity", "trade_profitability",
    "financial_score", "framework_score", "rank", "ranking", "winner", "best_framework",
    "recommendation",
}


def _normalized_field(name: object) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")
    return value


def prohibited_fields(payload: Any, prefix: str = "") -> tuple[str, ...]:
    found = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            normalized = _normalized_field(key)
            location = f"{prefix}.{key}" if prefix else str(key)
            if normalized in PROHIBITED_FIELD_TERMS:
                found.append(location)
            found.extend(prohibited_fields(value, location))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            found.extend(prohibited_fields(value, f"{prefix}[{index}]"))
    return tuple(found)


def enforce_structural_schema(payload: Any) -> None:
    found = prohibited_fields(payload)
    if found:
        raise ValueError(f"campaign structural output contains prohibited fields: {', '.join(found)}")


def aggregate_campaign_results(
    plan: HistoricalCampaignPlan,
    results: Iterable[HistoricalCampaignTaskResult],
) -> HistoricalCampaignAggregate:
    by_task = {result.task_id: result for result in results}
    rows = []
    completed = reused = logical_rows = chunks = valid_rows = skipped_rows = 0
    for task in plan.tasks:
        result = by_task.get(task.task_id)
        if result is None or result.status.value not in {"completed", "reused"}:
            continue
        completed += 1
        reused += int(result.status.value == "reused")
        logical_rows += result.logical_row_count
        chunks += result.chunk_count
        valid_rows += result.valid_row_count
        skipped_rows += result.skipped_row_count
        rows.append({
            "campaign_id": plan.campaign_id,
            "task_id": task.task_id,
            "child_run_id": result.child_run_id,
            "framework_name": task.framework_name,
            "framework_version": task.framework_version,
            "framework_configuration_fingerprint": task.framework_configuration_fingerprint,
            "source_set_name": task.source_set_name,
            "source_set_fingerprint": task.source_set_fingerprint,
            "source_fingerprints": dict(sorted(task.source_fingerprints.items())),
            "research_range": task.research_range.to_dict(),
            "task_status": result.status.value,
            "logical_row_count": result.logical_row_count,
            "chunk_count": result.chunk_count,
            "valid_row_count": result.valid_row_count,
            "skipped_row_count": result.skipped_row_count,
            "decision_direction_counts": dict(sorted(result.decision_direction_counts.items())),
            "lifecycle_state_counts": dict(sorted(result.lifecycle_state_counts.items())),
            "warning_count": result.warning_count,
            "validation_count": result.validation_count,
            "schema_fingerprint": result.child_schema_fingerprint,
            "code_fingerprint": plan.code_fingerprint,
        })
    enforce_structural_schema(rows)
    stable_payload = {
        "campaign_id": plan.campaign_id,
        "task_ordering": [row["task_id"] for row in rows],
        "rows": rows,
        "aggregate_version": "1.0",
    }
    fingerprint = stable_identity_hash(stable_payload)
    return HistoricalCampaignAggregate(
        campaign_id=plan.campaign_id,
        task_count=len(plan.tasks),
        completed_task_count=completed,
        reused_task_count=reused,
        logical_row_count=logical_rows,
        chunk_count=chunks,
        valid_row_count=valid_rows,
        skipped_row_count=skipped_rows,
        task_rows=tuple(rows),
        aggregate_fingerprint=fingerprint,
    )


def write_campaign_aggregate(campaign_directory: str | Path, aggregate: HistoricalCampaignAggregate) -> Path:
    root = Path(campaign_directory) / "summaries"
    root.mkdir(parents=True, exist_ok=True)
    target = root / "structural_summary.csv"
    temporary = target.with_name(target.name + ".tmp")
    fields = [
        "campaign_id", "task_id", "child_run_id", "framework_name", "framework_version",
        "framework_configuration_fingerprint", "source_set_name", "source_set_fingerprint",
        "research_range", "task_status", "logical_row_count", "chunk_count", "valid_row_count",
        "skipped_row_count", "decision_direction_counts", "lifecycle_state_counts", "warning_count",
        "validation_count", "schema_fingerprint", "code_fingerprint",
    ]
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in aggregate.task_rows:
            serializable = dict(row)
            for name in ("research_range", "decision_direction_counts", "lifecycle_state_counts"):
                serializable[name] = stable_json(serializable[name])
            writer.writerow(serializable)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
    atomic_json(root / "structural_summary_manifest.json", aggregate.to_dict())
    return target


def stable_json(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
