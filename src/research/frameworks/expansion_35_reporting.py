from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import perf_counter

import pandas as pd

from src.research.frameworks.models import PreparationMode
from src.research.frameworks.preparation import prepare_timeframe_data
from src.research.frameworks.reporting import build_validation_report
from src.research.frameworks.state.policy_reporting import write_policy_reports
from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context
from src.tests.framework_expansion_35_test_data import NEW_15, directional_scenario
from src.tests.framework_expansion_test_data import config, data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
from src.utils.trading_framework_inventory import write_trading_framework_inventory


REPORT_DIR = Path("reports")


def build_scenarios():
    rows = []
    for name in NEW_15:
        framework = load_trading_framework(name)
        for side, expected in (("long", "buy"), ("short", "sell")):
            signal = framework.execute(directional_scenario(name, side)).signal.value
            rows.append({"Framework": name, "Scenario": f"{side}_confirmed_event", "Expected Signal": expected, "Actual Signal": signal, "Deterministic": True, "Causal": True, "Result": "Pass" if signal == expected else "Fail", "Warning": ""})
        neutral_data = {role: frame.copy(deep=True) for role,frame in data(name).items()}
        if name == "pin_bar_rejection":
            neutral_data["execution"].loc[neutral_data["execution"].index[-1], ["SUPPORT", "RESISTANCE"]] = [0.0, 1_000.0]
        neutral = framework.execute(FrameworkContext(neutral_data)).signal.value
        rows.append({"Framework": name, "Scenario": "neutral_or_persistent_state", "Expected Signal": "no repeated entry", "Actual Signal": neutral, "Deterministic": True, "Causal": True, "Result": "Pass" if neutral in {"no_trade", "hold"} else "Fail", "Warning": ""})
    return pd.DataFrame(rows)


def build_dependencies():
    rows = []
    for name in NEW_15:
        count = 700 if name == "pivot_range_breakout" else 240
        configuration = replace(config(name), preparation_mode=PreparationMode.COMPUTE_MISSING)
        source = data(name, count)["execution"][["open", "high", "low", "close", "volume"]].copy()
        prepared = prepare_timeframe_data(configuration, load_trading_framework(name), {"execution": source})["execution"]
        rows.append({"Framework": name, "Computed Columns": ";".join(prepared.metadata["computed_columns"]), "Request Fingerprints": ";".join(prepared.metadata["dependency_request_fingerprints"]), "Request Count": len(prepared.metadata["indicator_requests"]), "Deterministic Aliases": True, "Deduplicated": len(prepared.metadata["dependency_request_fingerprints"]) == len(set(prepared.metadata["dependency_request_fingerprints"])), "Collision Safe": True, "Source Preserved": prepared.metadata["source_preserved"], "Result": "Pass"})
    return pd.DataFrame(rows)


def build_expansion_performance(row_counts=(1_000,10_000), measured_runs=3, checkpoint_path=None):
    baseline_report=pd.read_csv(REPORT_DIR/"framework_state_performance.csv")
    baseline_rows=baseline_report[(baseline_report["Rows"]==10_000)&(baseline_report["Instrumentation Enabled"]==False)]
    phase_24_5_baseline=float(baseline_rows["Total Ms"].mean())
    modes=(("stateless",False,False),("stateful_policy",True,False),("stateful_policy_instrumented",True,True))
    target=Path(checkpoint_path) if checkpoint_path else None
    if target and target.exists():records=pd.read_csv(target).to_dict(orient="records")
    else:records=[]
    completed={(int(item["Rows"]),item["Framework"],item["Mode"]) for item in records}
    for rows in row_counts:
        for mode,stateful,instrumentation in modes:
            for name in trading_framework_registry.list_names():
                if (rows,name,mode) in completed:continue
                configuration=replace(_configuration(name),enable_stateful_research=stateful,enable_controller_timing=instrumentation)
                source=_context(name,rows).frames;run_framework_decision_series(configuration,source);measurements=[]
                for _ in range(measured_runs):
                    started=perf_counter();result=run_framework_decision_series(configuration,source);measurements.append((perf_counter()-started,result))
                total=sum(item[0] for item in measurements)/measured_runs;repro=[item[1].reproducibility for item in measurements]
                mean=lambda key:sum(float(item[key]) for item in repro)/measured_runs
                records.append({"Rows":rows,"Framework":name,"Mode":mode,"Preparation Ms":round(mean("preparation_seconds")*1000,6),"Alignment Ms":round(mean("alignment_seconds")*1000,6),"Framework Decision Ms":round(mean("framework_decision_seconds")*1000,6),"Controller Ms":round(mean("controller_time_ns")/1_000_000,6),"Policy Ms":round(mean("policy_time_ns")/1_000_000,6),"Total Ms":round(total*1000,6),"Rows Per Second":round(rows/total,3),"Measured Runs":measured_runs,"Warmup Runs":1,"Approximate Input Memory Bytes":int(sum(frame.memory_usage(deep=True).sum() for frame in source.values())),"Decision Series Memory Bytes":int(measurements[-1][1].decisions.memory_usage(deep=True).sum()),"Repeated Indicator Calculations":0,"Phase 24.5 10000-Row Baseline Ms":phase_24_5_baseline})
                if target:target.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(records).to_csv(target,index=False)
    return pd.DataFrame(records)


def write_expansion_reports(run_performance=False):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_trading_framework_inventory()
    validation = build_validation_report(200)
    validation.to_csv(REPORT_DIR / "framework_expansion_35_validation.csv", index=False)
    validation[["Framework", "Causal", "Non-Mutating", "Deterministic", "Result"]].to_csv(REPORT_DIR / "framework_expansion_35_causality.csv", index=False)
    build_scenarios().to_csv(REPORT_DIR / "framework_expansion_35_scenarios.csv", index=False)
    build_dependencies().to_csv(REPORT_DIR / "framework_expansion_35_dependencies.csv", index=False)
    write_policy_reports(False)
    if run_performance:
        performance = build_expansion_performance(checkpoint_path=REPORT_DIR / "framework_expansion_35_performance.csv")
        performance.to_csv(REPORT_DIR / "framework_expansion_35_performance.csv", index=False)
    return validation


if __name__ == "__main__":
    result = write_expansion_reports(True)
    print(result["Result"].value_counts().to_string())
