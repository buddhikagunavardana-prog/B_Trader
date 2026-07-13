import copy
import json
from pathlib import Path

import pandas as pd

from src.ai.research.research_analyst import load_ai_research_config
from src.research.generated_candidate_experiment import _run_records
from src.research.pipeline.pipeline_loader import load_market_data
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report
from src.strategies.strategy_factory import create_strategy_from_json_config


def _record(config: dict, source: str, template_type: str) -> dict:
    return {
        "strategy_id": config["strategy_id"],
        "strategy_name": config["name"],
        "strategy_source": source,
        "template_type": template_type,
        "strategy": create_strategy_from_json_config(config),
    }


def _group_metrics(report: pd.DataFrame, source: str) -> dict:
    rows = report[report["Strategy Source"] == source]
    return {
        "rows": int(len(rows)),
        "mean_profit_factor": round(float(rows["Profit Factor"].mean()), 4),
        "mean_raw_profit_factor": round(float(rows["Raw Profit Factor"].mean()), 4),
        "mean_raw_expectancy_pct": round(float(rows["Raw Expectancy %"].mean()), 4),
        "mean_roi_pct": round(float(rows["ROI %"].mean()), 4),
        "mean_max_drawdown_pct": round(float(rows["Max Drawdown %"].mean()), 4),
        "mean_trades": round(float(rows["Trades"].mean()), 2),
    }


def _matched_baseline(candidate: dict) -> dict:
    baseline = copy.deepcopy(candidate)
    baseline["strategy_id"] = f"MATCHED_{candidate['strategy_id']}_NO_VOLUME"
    baseline["name"] = f"{candidate['name']} without volume confirmation"
    baseline["indicators"].pop("volume", None)
    baseline["entry_rules"].pop("volume_confirmation", None)
    baseline["metadata"] = {
        **baseline.get("metadata", {}),
        "origin": "DERIVED_MATCHED_BASELINE",
        "matched_difference": "volume_confirmation_removed",
    }
    return baseline


def run_reviewed_proposal_experiment(
    config_override: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    config = load_ai_research_config()
    if config_override:
        config.update(config_override)
    if not config["enable_reviewed_proposal_experiment"]:
        return pd.DataFrame(), {
            "status": "DISABLED",
            "deterministic_benchmark_unchanged": True,
        }
    with open(config["candidate_definition_output_path"], "r", encoding="utf-8") as file:
        definitions = json.load(file)
    candidates = definitions.get("candidate_definitions", [])
    if len(candidates) != 1:
        raise ValueError("Controlled experiment requires exactly one candidate")
    baseline = _matched_baseline(candidates[0])
    records = [
        _record(baseline, "MATCHED_BASELINE", "fixed"),
        _record(candidates[0], "AI_REVIEWED", "ai_reviewed"),
    ]
    pairs = list(candidates[0].get("metadata", {}).get("market_scope", []))
    if not pairs:
        pairs = list(config["allowed_market_scope"])
    timeframe = candidates[0]["timeframe"]
    market_data = load_market_data(pairs, timeframe, "1 year ago UTC")
    report, runtime = _run_records(records, market_data, pairs, timeframe)
    save_csv_report(report, config["proposal_experiment_report_path"])
    baseline_metrics = _group_metrics(report, "MATCHED_BASELINE")
    proposal_metrics = _group_metrics(report, "AI_REVIEWED")
    summary = {
        "status": "COMPLETED",
        "experiment_type": "CONTROLLED_RESEARCH_ONLY",
        "proposal_id": candidates[0]["metadata"]["proposal_id"],
        "matched_baseline_strategy_id": baseline["strategy_id"],
        "pairs": pairs,
        "timeframe": timeframe,
        "runtime_seconds": round(runtime, 4),
        "matched_baseline": baseline_metrics,
        "reviewed_proposal": proposal_metrics,
        "difference": {
            "mean_profit_factor": round(
                proposal_metrics["mean_profit_factor"]
                - baseline_metrics["mean_profit_factor"], 4
            ),
            "mean_raw_expectancy_pct": round(
                proposal_metrics["mean_raw_expectancy_pct"]
                - baseline_metrics["mean_raw_expectancy_pct"], 4
            ),
            "mean_roi_pct": round(
                proposal_metrics["mean_roi_pct"]
                - baseline_metrics["mean_roi_pct"], 4
            ),
            "mean_max_drawdown_pct": round(
                proposal_metrics["mean_max_drawdown_pct"]
                - baseline_metrics["mean_max_drawdown_pct"], 4
            ),
        },
        "paper_trading_readiness": "UNCHANGED_NOT_READY",
        "production_activation_allowed": False,
        "conclusion": (
            "Initial matched backtest only; unchanged funnel and robustness "
            "validation are still required before any promotion claim."
        ),
    }
    save_json_report(summary, config["proposal_experiment_summary_path"])
    return report, summary
