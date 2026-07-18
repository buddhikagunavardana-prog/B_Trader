from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.validator import validate_registry


REPORT_PATH = Path("reports/trading_framework_inventory.csv")


def build_trading_framework_inventory() -> pd.DataFrame:
    validation = validate_registry()
    validation_text = "Pass" if validation.valid else "Fail"
    rows = []
    root = Path.cwd().resolve()
    for number, definition in enumerate(trading_framework_registry.list_definitions(), start=1):
        metadata = definition["metadata"]
        source = Path(definition["source_file"]).resolve()
        try:
            source_path = source.relative_to(root).as_posix()
        except ValueError:
            source_path = source.as_posix()
        rows.append({
            "Number": number,
            "Canonical Name": metadata["name"],
            "Display Name": metadata["display_name"],
            "Category": metadata["category"],
            "Version": metadata["version"],
            "Stability": metadata["stability"],
            "Supported Markets": "; ".join(metadata["supported_markets"]),
            "Supported Directions": "; ".join(metadata["supported_directions"]),
            "Required Timeframes": json.dumps(metadata["default_timeframes"], sort_keys=True),
            "Required Indicators": "; ".join(metadata["required_indicators"]),
            "Parameter Count": len(definition["schema"]["parameters"]),
            "Source Path": source_path,
            "Validation Result": validation_text,
            "Notes": metadata["reference_notes"],
        })
    return pd.DataFrame(rows)


def write_trading_framework_inventory(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_trading_framework_inventory().to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_trading_framework_inventory())
