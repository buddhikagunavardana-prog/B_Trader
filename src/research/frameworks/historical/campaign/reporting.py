from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable, Mapping

from src.research.frameworks.historical.campaign.aggregation import enforce_structural_schema


CAMPAIGN_REPORT_FILES = {
    "plan": "phase_24_9_campaign_plan_validation.csv",
    "execution": "phase_24_9_campaign_execution_validation.csv",
    "resume_recovery": "phase_24_9_campaign_resume_recovery_validation.csv",
    "integrity": "phase_24_9_campaign_integrity_validation.csv",
    "structural_summary": "phase_24_9_campaign_structural_summary_validation.csv",
    "all_35": "phase_24_9_campaign_all_35_compatibility.csv",
    "causality": "phase_24_9_campaign_causality_validation.csv",
    "memory": "phase_24_9_campaign_memory_validation.csv",
    "scope_exclusion": "phase_24_9_campaign_scope_exclusion_validation.csv",
    "security": "phase_24_9_campaign_security_validation.csv",
}


def write_campaign_validation_reports(
    records_by_name: Mapping[str, Iterable[Mapping[str, object]]],
    report_directory: str | Path = "reports",
) -> tuple[Path, ...]:
    unknown = sorted(set(records_by_name) - set(CAMPAIGN_REPORT_FILES))
    if unknown:
        raise ValueError(f"unknown campaign validation report names: {', '.join(unknown)}")
    root = Path(report_directory)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for name in CAMPAIGN_REPORT_FILES:
        rows = [dict(row) for row in records_by_name.get(name, ())]
        if not rows:
            raise ValueError(f"campaign validation report has no evidence rows: {name}")
        enforce_structural_schema(rows)
        fields = sorted({key for row in rows for key in row})
        target = root / CAMPAIGN_REPORT_FILES[name]
        temporary = target.with_name(target.name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        written.append(target)
    return tuple(written)
