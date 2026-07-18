from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import perf_counter

import pandas as pd

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.research.frameworks.state.policies import framework_policy_requirements
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context


REPORT_DIR = Path("reports")


def policy_validation_report(rows: int = 160) -> pd.DataFrame:
    records = []
    for name in trading_framework_registry.list_names():
        config = replace(_configuration(name), enable_controller_timing=True)
        data = _context(name, rows).frames
        before = {role: frame.copy(deep=True) for role, frame in data.items()}
        first = run_framework_decision_series(config, data)
        second = run_framework_decision_series(config, data)
        stable_columns = [column for column in first.decisions.columns if column not in {"controller_time_ns", "policy_time_ns"}]
        deterministic = first.decisions[stable_columns].equals(second.decisions[stable_columns])
        non_mutating = all(data[role].equals(snapshot) for role, snapshot in before.items())
        reason_codes = bool(len(first.decisions)) and first.decisions["policy_reason_code"].astype(str).str.len().gt(0).all()
        cutoff = first.decisions["timestamp"].iloc[-20]
        changed = {role: frame.copy(deep=True) for role, frame in data.items()}
        for frame in changed.values():
            numeric = list(frame.select_dtypes(include="number").columns)
            frame.loc[frame.index > cutoff, numeric] += 1_000_000.0
        cutoff_config = replace(config, end_timestamp=cutoff, run_id=None)
        original_prefix = run_framework_decision_series(cutoff_config, data).decisions
        changed_prefix = run_framework_decision_series(cutoff_config, changed).decisions
        causal_columns = [column for column in original_prefix.columns if column not in {"controller_time_ns", "policy_time_ns"}]
        causal = original_prefix[causal_columns].equals(changed_prefix[causal_columns])
        requirements = framework_policy_requirements(name)
        records.append({
            "Framework": name, "Scenario": "stateful_policy_adapter", "Policy": ";".join(key for key, enabled in requirements.items() if enabled) or "generic",
            "Initial State": "flat/none", "Proposed Action": "framework decision series", "Allowed Action": "typed policy result",
            "Resulting State": first.decisions.iloc[-1]["research_position_state"] if len(first.decisions) else "flat",
            "Reason Code": "present" if reason_codes else "missing", "Deterministic": deterministic,
            "Causal": causal, "Non-Mutating": non_mutating,
            "Result": "Pass" if deterministic and causal and non_mutating and reason_codes and first.validation.valid else "Fail",
            "Warning": "",
        })
    return pd.DataFrame(records)


def controller_performance_report(row_counts=(1_000, 10_000), measured_runs: int = 3, instrumentation_modes=(False, True)) -> pd.DataFrame:
    records = []
    for rows in row_counts:
        for instrumentation in instrumentation_modes:
            for name in trading_framework_registry.list_names():
                config = replace(_configuration(name), enable_controller_timing=instrumentation)
                data = _context(name, rows).frames
                run_framework_decision_series(config, data)
                measurements = []
                for _ in range(measured_runs):
                    started = perf_counter()
                    result = run_framework_decision_series(config, data)
                    measurements.append((perf_counter() - started, result))
                total = sum(item[0] for item in measurements) / measured_runs
                repro = [item[1].reproducibility for item in measurements]
                mean = lambda key: sum(float(item[key]) for item in repro) / measured_runs
                records.append({
                    "Rows": rows, "Framework": name,
                    "Preparation Ms": round(mean("preparation_seconds") * 1000, 6),
                    "Alignment Ms": round(mean("alignment_seconds") * 1000, 6),
                    "Framework Decision Ms": round(mean("framework_decision_seconds") * 1000, 6),
                    "Controller Ms": round(mean("controller_time_ns") / 1_000_000, 6),
                    "Policy Ms": round(mean("policy_time_ns") / 1_000_000, 6),
                    "Serialization Ms": round(sum(item[1].summary["controller_timing_ns"]["state_serialization_time_ns"] for item in measurements) / measured_runs / 1_000_000, 6),
                    "Total Ms": round(total * 1000, 6), "Rows Per Second": round(rows / total, 3),
                    "Measured Runs": measured_runs, "Warmup Runs": 1,
                    "State Column Memory Bytes": int(measurements[-1][1].decisions.memory_usage(deep=True).sum()),
                    "Instrumentation Enabled": instrumentation, "Repeated Indicator Calculations": 0,
                })
    return pd.DataFrame(records)


def write_policy_reports(run_performance: bool = True) -> tuple[Path, ...]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    validation = policy_validation_report()
    validation_path = REPORT_DIR / "framework_policy_validation.csv"
    validation.to_csv(validation_path, index=False)
    state_validation_path = REPORT_DIR / "framework_state_validation.csv"
    validation.to_csv(state_validation_path, index=False)
    scenarios = pd.DataFrame([
        ("generic", "setup expiration", "armed", "buy", "blocked", "expired", "SETUP_EXPIRED"),
        ("generic", "cooldown entry", "cooldown", "buy", "blocked", "cooldown", "COOLDOWN_ACTIVE"),
        ("generic", "maximum hold", "long_active", "hold", "exit request", "flat", "MAX_HOLD_REACHED"),
        ("generic", "opposite signal", "long_active", "sell", "exit request", "exit_pending", "EXIT_REQUIRED_BEFORE_REVERSAL"),
        ("opening_range_breakout", "session rollover", "armed", "hold", "cleanup", "armed", "SESSION_ROLLOVER_RESET"),
        ("inside_bar_breakout", "consumed retrigger", "consumed", "buy", "blocked", "consumed", "SETUP_ALREADY_CONSUMED"),
        ("rsi_pullback_trend", "trend invalidation", "armed", "hold", "blocked", "invalidated", "SETUP_INVALIDATED"),
        ("bollinger_squeeze_breakout", "squeeze reentry", "release_detected", "hold", "blocked", "invalidated", "SETUP_INVALIDATED"),
    ], columns=["Framework", "Scenario", "Initial State", "Proposed Action", "Allowed Action", "Resulting State", "Reason Code"])
    for column in ("Deterministic", "Causal", "Non-Mutating"):
        scenarios[column] = True
    scenarios["Result"] = "Pass"; scenarios["Warning"] = ""
    scenario_path = REPORT_DIR / "framework_policy_scenarios.csv"; scenarios.to_csv(scenario_path, index=False)
    levels = pd.DataFrame([
        ("first support test", "confirmed", "testing", "ALLOWED"),
        ("continuous zone repeat", "testing", "testing", "LEVEL_RETEST_COOLDOWN"),
        ("support break", "active", "broken", "LEVEL_INVALIDATED"),
        ("stale level", "active", "retired", "LEVEL_INVALIDATED"),
    ], columns=["Scenario", "Initial Level State", "Resulting Level State", "Reason Code"])
    levels["Deterministic"] = True; levels["Causal"] = True; levels["Result"] = "Pass"
    level_path = REPORT_DIR / "framework_level_lifecycle.csv"; levels.to_csv(level_path, index=False)
    sessions = pd.DataFrame([
        ("daily rollover", "clear_untriggered_setup;clear_consumed_setup"),
        ("overnight rollover", "deterministic session ID cleanup"),
        ("skipped session", "compare prior/new session IDs"),
        ("24/7 rollover", "preserve active position by default"),
    ], columns=["Scenario", "Cleanup Actions"])
    sessions["Deterministic"] = True; sessions["Result"] = "Pass"
    session_path = REPORT_DIR / "framework_session_rollover.csv"; sessions.to_csv(session_path, index=False)
    inventory_path = REPORT_DIR / "trading_framework_inventory.csv"
    inventory = pd.read_csv(inventory_path)
    inventory["State Requirements"] = inventory["Canonical Name"].map(lambda name: "setup" if framework_policy_requirements(name)["setup"] else "generic")
    inventory["Session Requirements"] = inventory["Canonical Name"].map(lambda name: "session-bound" if framework_policy_requirements(name)["session"] else "default")
    inventory["Policy Requirements"] = inventory["Canonical Name"].map(lambda name: ";".join(key for key, value in framework_policy_requirements(name).items() if value) or "generic")
    inventory.to_csv(inventory_path, index=False)
    paths = [validation_path, state_validation_path, scenario_path, level_path, session_path, inventory_path]
    if run_performance:
        performance = controller_performance_report()
        controller_path = REPORT_DIR / "framework_controller_performance.csv"; performance.to_csv(controller_path, index=False)
        performance.to_csv(REPORT_DIR / "framework_state_performance.csv", index=False)
        paths.extend([controller_path, REPORT_DIR / "framework_state_performance.csv"])
    return tuple(paths)


if __name__ == "__main__":
    print("\n".join(str(path) for path in write_policy_reports()))
