from __future__ import annotations

from pathlib import Path

import pandas as pd


COMPONENTS = (
    ("models", "Typed research configuration, prepared data, alignment, validation, and result models", "src/research/frameworks/models.py", "models; configuration"),
    ("configuration", "Versioned JSON persistence and experimental controls", "src/research/frameworks/configuration.py", "configuration"),
    ("preparation", "Precomputed-only and explicit compute-missing preparation", "src/research/frameworks/preparation.py", "preparation; causality"),
    ("alignment", "Backward-as-of completed-bar alignment", "src/research/frameworks/alignment.py", "alignment; causality"),
    ("adapter", "Chronological normalized decision-series generation", "src/research/frameworks/adapter.py", "decision series; causality"),
    ("validator", "Structured output and repeatability validation", "src/research/frameworks/validator.py", "validation"),
    ("reporting", "Deterministic inventory, validation, and performance reports", "src/research/frameworks/reporting.py", "reporting"),
)


def build_adapter_inventory() -> pd.DataFrame:
    return pd.DataFrame([
        {"Adapter Component": name, "Responsibility": responsibility, "Status": "Complete", "Source Path": path, "Test Coverage": tests, "Notes": "Phase 24.2 deterministic foundation"}
        for name, responsibility, path, tests in COMPONENTS
    ])


def write_adapter_inventory(path: str | Path = "reports/framework_research_adapter_inventory.csv") -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    build_adapter_inventory().to_csv(target, index=False)
    return target
