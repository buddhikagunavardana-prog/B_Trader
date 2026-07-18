from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pandas as pd

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.inventory import write_adapter_inventory
from src.research.frameworks.models import FrameworkResearchConfiguration
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context


def _configuration(name: str) -> FrameworkResearchConfiguration:
    metadata = trading_framework_registry.resolve(name).schema.metadata
    primary = trading_framework_registry.resolve(name).execution_role
    return FrameworkResearchConfiguration(name, metadata.version, {}, "SYNTHETIC-USD", "crypto_spot", metadata.default_timeframes, primary)


def build_validation_report(rows: int = 200) -> pd.DataFrame:
    records = []
    for name in trading_framework_registry.list_names():
        config = _configuration(name); data = _context(name, rows).frames
        snapshots = {role: frame.copy(deep=True) for role, frame in data.items()}
        first = run_framework_decision_series(config, data)
        second = run_framework_decision_series(config, data)
        deterministic = first.decisions.equals(second.decisions)
        non_mutating = all(data[role].equals(before) for role, before in snapshots.items())
        cutoff = first.decisions["timestamp"].iloc[-20]
        cutoff_data = {role: frame.copy(deep=True) for role, frame in data.items()}
        for frame in cutoff_data.values():
            future = frame.index > cutoff; numeric = list(frame.select_dtypes(include="number").columns)
            frame.loc[future, numeric] = frame.loc[future, numeric] + 1_000_000.0
        cutoff_config_data = config.to_dict(); cutoff_config_data["end_timestamp"] = cutoff.isoformat()
        cutoff_config = FrameworkResearchConfiguration(**cutoff_config_data)
        causal = run_framework_decision_series(cutoff_config, data).decisions.equals(run_framework_decision_series(cutoff_config, cutoff_data).decisions)
        records.append({
            "Framework": name, "Scenario": "deterministic_precomputed", "Rows": rows,
            "Deterministic": deterministic, "Causal": causal, "Non-Mutating": non_mutating,
            "Output Valid": first.validation.valid, "Warnings": len(first.warnings),
            "Result": "Pass" if all((deterministic, causal, non_mutating, first.validation.valid)) else "Fail",
        })
    return pd.DataFrame(records)


def build_performance_report(row_counts=(1_000, 10_000), measured_runs: int = 3) -> pd.DataFrame:
    records = []
    for rows in row_counts:
        for name in trading_framework_registry.list_names():
            config = _configuration(name); data = _context(name, rows).frames
            run_framework_decision_series(config, data)
            timings = []
            for _ in range(measured_runs):
                started = perf_counter(); result = run_framework_decision_series(config, data); total = perf_counter() - started
                timings.append((total, result))
            average_total = sum(item[0] for item in timings) / measured_runs
            prep = sum(item[1].reproducibility["preparation_seconds"] for item in timings) / measured_runs
            align = sum(item[1].reproducibility["alignment_seconds"] for item in timings) / measured_runs
            decisions = sum(item[1].reproducibility["decision_generation_seconds"] for item in timings) / measured_runs
            memory = sum(frame.memory_usage(deep=True).sum() for frame in data.values())
            records.append({
                "Rows": rows, "Framework": name, "Preparation Ms": round(prep * 1000, 6),
                "Alignment Ms": round(align * 1000, 6), "Decision Series Ms": round(decisions * 1000, 6),
                "Total Ms": round(average_total * 1000, 6), "Rows Per Second": round(rows / average_total, 3),
                "Measured Runs": measured_runs, "Warmup Runs": 1, "Approximate Input Memory Bytes": int(memory),
                "Repeated Indicator Calculations": 0,
            })
    return pd.DataFrame(records)


def write_release_reports() -> tuple[Path, Path, Path]:
    inventory = write_adapter_inventory()
    validation = Path("reports/framework_decision_series_validation.csv")
    performance = Path("reports/framework_research_adapter_performance.csv")
    build_validation_report().to_csv(validation, index=False)
    build_performance_report().to_csv(performance, index=False)
    return inventory, validation, performance


if __name__ == "__main__":
    print(write_release_reports())
