from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research.frameworks.profiling.models import ExecutionMode, PerformanceBudget
from src.research.frameworks.profiling.profiler import profile_framework
from src.research.frameworks.profiling.validation import evaluate_budget, multi_cutoff_causality_report
from src.research.frameworks.reporting import _configuration
from src.research.frameworks.adapter import run_framework_decision_series
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context


def measurements_frame(measurements) -> pd.DataFrame:
    return pd.DataFrame([measurement.to_dict() for measurement in measurements])


def hotspot_frame(profile: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    if profile.empty:
        return profile.copy()
    return profile.sort_values(["median_ms", "memory_bytes"], ascending=False).head(limit).copy()


def profile_matrix(row_counts=(1_000, 10_000), measured_runs=5, checkpoint_path=None):
    target = Path(checkpoint_path) if checkpoint_path else None
    if target and target.exists():
        records = pd.read_csv(target).to_dict(orient="records")
    else:
        records = []
    completed = {(int(row["row_count"]), row["framework"], row["mode"]) for row in records}
    for rows in row_counts:
        for mode in ExecutionMode:
            for name in trading_framework_registry.list_names():
                key = (rows, name, mode.value)
                if key in completed:
                    continue
                measurement = profile_framework(
                    _configuration(name), _context(name, rows).frames, mode,
                    warmup_runs=1, measured_runs=measured_runs,
                )
                records.append(measurement.to_dict())
                if target:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    pd.DataFrame(records).to_csv(target, index=False)
    return pd.DataFrame(records)


def _baseline_lookup():
    preserved = Path("reports/framework_performance_before_after.csv")
    if preserved.exists():
        comparison = pd.read_csv(preserved)
        if {"row_count", "framework", "mode", "baseline_ms"}.issubset(comparison.columns):
            return {
                (int(row["row_count"]), row["framework"], row["mode"]): float(row["baseline_ms"])
                for _, row in comparison.iterrows()
            }
    baseline = pd.read_csv("reports/framework_expansion_35_performance.csv")
    return {
        (int(row["Rows"]), row["Framework"], row["Mode"]): float(row["Total Ms"])
        for _, row in baseline.iterrows()
    }


def performance_budget_frame(profile: pd.DataFrame) -> pd.DataFrame:
    budget = PerformanceBudget()
    budget_rows = []
    for name in trading_framework_registry.list_names():
        by_name = profile[profile["framework"] == name]
        stateful_1k = by_name[(by_name["row_count"] == 1_000) & (by_name["mode"] == ExecutionMode.STATEFUL_POLICY.value)]
        stateful_10k = by_name[(by_name["row_count"] == 10_000) & (by_name["mode"] == ExecutionMode.STATEFUL_POLICY.value)]
        timed_10k = by_name[(by_name["row_count"] == 10_000) & (by_name["mode"] == ExecutionMode.STATEFUL_POLICY_INSTRUMENTED.value)]
        scaling = float(stateful_10k.iloc[0]["median_ms"] / stateful_1k.iloc[0]["median_ms"])
        overhead = float((timed_10k.iloc[0]["median_ms"] / stateful_10k.iloc[0]["median_ms"] - 1.0) * 100.0)
        memory_ratio = float(stateful_10k.iloc[0]["memory_bytes"] / stateful_1k.iloc[0]["memory_bytes"])
        repeated = int(by_name["repeated_indicator_calculations"].max())
        outcome = evaluate_budget(overhead, scaling, repeated, memory_ratio, budget)
        budget_rows.append({
            "framework": name, "instrumentation_overhead_percent": overhead,
            "scaling_ratio": scaling, "memory_growth_ratio": memory_ratio,
            "repeated_indicator_calculations": repeated, "budget_status": outcome["status"],
            "warnings": ";".join(outcome["warnings"]), "blockers": ";".join(outcome["blockers"]),
        })
    return pd.DataFrame(budget_rows)


def write_optimization_reports(profile: pd.DataFrame, report_dir="reports"):
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "framework_profiling_summary.csv"
    profile.to_csv(summary_path, index=False)
    baseline = _baseline_lookup()
    comparisons = profile.copy()
    comparisons["baseline_ms"] = comparisons.apply(
        lambda row: baseline.get(
            (int(row["row_count"]), row["framework"], row["mode"]),
            baseline.get((int(row["row_count"]), row["framework"], "stateful_policy")),
        ), axis=1,
    )
    comparisons["optimized_ms"] = comparisons["median_ms"]
    comparisons["percentage_change"] = (comparisons["optimized_ms"] / comparisons["baseline_ms"] - 1.0) * 100.0
    comparisons.to_csv(destination / "framework_performance_before_after.csv", index=False)

    hotspot_columns = [
        "framework", "category", "row_count", "mode", "median_ms", "memory_bytes",
        "preparation_ms", "alignment_ms", "decision_ms", "controller_ms", "policy_ms",
        "session_ms", "setup_ms", "position_ms", "diagnostics_ms", "normalization_ms",
        "serialization_ms", "manifest_ms",
    ]
    profile.sort_values(["median_ms", "memory_bytes"], ascending=False).head(35)[hotspot_columns].to_csv(
        destination / "framework_hotspot_analysis.csv", index=False,
    )
    profile[["framework", "category", "row_count", "mode", "memory_bytes"]].to_csv(
        destination / "framework_memory_profile.csv", index=False,
    )

    instrumented = profile[profile["mode"] == ExecutionMode.STATEFUL_POLICY_INSTRUMENTED.value].copy()
    instrumented.to_csv(destination / "framework_controller_performance.csv", index=False)

    performance_budget_frame(profile).to_csv(destination / "framework_performance_budgets.csv", index=False)

    expansion = profile.rename(columns={
        "row_count": "Rows", "framework": "Framework", "mode": "Mode",
        "preparation_ms": "Preparation Ms", "alignment_ms": "Alignment Ms",
        "decision_ms": "Framework Decision Ms", "controller_ms": "Controller Ms",
        "policy_ms": "Policy Ms", "mean_ms": "Total Ms", "measured_runs": "Measured Runs",
        "warmup_runs": "Warmup Runs", "memory_bytes": "Decision Series Memory Bytes",
        "repeated_indicator_calculations": "Repeated Indicator Calculations",
    }).copy()
    expansion["Rows Per Second"] = expansion["Rows"] / (expansion["Total Ms"] / 1000.0)
    expansion.to_csv(destination / "framework_expansion_35_performance.csv", index=False)
    return tuple(destination / name for name in (
        "framework_profiling_summary.csv", "framework_hotspot_analysis.csv",
        "framework_performance_before_after.csv", "framework_memory_profile.csv",
        "framework_performance_budgets.csv", "framework_controller_performance.csv",
        "framework_expansion_35_performance.csv",
    ))


def write_equivalence_and_causality_reports(report_dir="reports", rows=200):
    from dataclasses import replace

    destination = Path(report_dir)
    equivalence = []
    ignored = {"diagnostics", "controller_time_ns", "policy_time_ns"}
    for name in trading_framework_registry.list_names():
        source = _context(name, rows).frames
        base_configuration = replace(
            _configuration(name), state_diagnostics_level="standard",
            persist_state_snapshots=False, enable_controller_timing=False, run_id=None,
        )
        baseline = run_framework_decision_series(base_configuration, source).decisions
        stable = [column for column in baseline.columns if column not in ignored]
        level_equal = True
        for level in ("none", "summary", "full"):
            candidate = run_framework_decision_series(
                replace(base_configuration, state_diagnostics_level=level, run_id=None), source,
            ).decisions
            level_equal = level_equal and baseline[stable].equals(candidate[stable])
        snapshot_equal = True
        for mode in ("final_only", "transitions_only", "full"):
            candidate = run_framework_decision_series(
                replace(base_configuration, persist_state_snapshots=mode, run_id=None), source,
            ).decisions
            snapshot_equal = snapshot_equal and baseline.equals(candidate)
        equivalence.append({
            "Framework": name, "Decision Fields Equal": level_equal,
            "Diagnostic Level Invariant": level_equal, "Snapshot Mode Invariant": snapshot_equal,
            "Timing Fields Excluded": True,
            "Result": "Pass" if level_equal and snapshot_equal else "Fail",
        })
    equivalence_frame = pd.DataFrame(equivalence)
    equivalence_frame.to_csv(destination / "framework_output_equivalence.csv", index=False)
    causality = multi_cutoff_causality_report(rows)
    causality.to_csv(destination / "framework_optimization_causality.csv", index=False)
    return equivalence_frame, causality
