import json
import math
from pathlib import Path

import pandas as pd

from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_runner import run_monte_carlo_validation
from src.research.orchestrator.adapters.adapter_result import (
    FAILURE_ARTIFACT,
    artifact_path_from_state,
    benchmark_settings,
    blocked_payload,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


TRADE_COLUMNS = [
    "Candidate ID", "Strategy ID", "Strategy Name", "Template Type", "Pair",
    "Timeframe", "Trade ID", "Entry Time", "Exit Time", "PnL", "PnL %",
    "Fees", "Initial Balance",
]
MONTE_CARLO_RESULT_COLUMNS = [
    "Candidate ID", "Strategy ID", "Pair", "Timeframe", "Simulation Index",
    "Seed", "Final Balance", "ROI %", "Max Drawdown %", "Trade Count",
    "Positive Run", "Ruin", "Failure Reason",
]


def _load_shortlist(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise ValueError("ARTIFACT_CONTRACT_FAILURE: robustness shortlist must be a list")
    return payload


def _load_candidate_trades(path: str) -> pd.DataFrame:
    report = pd.read_csv(path)
    missing = [column for column in TRADE_COLUMNS if column not in report.columns]
    if missing:
        raise ValueError(
            f"ARTIFACT_CONTRACT_FAILURE: candidate trades missing columns {missing}"
        )
    numeric_columns = ["Trade ID", "PnL", "PnL %", "Fees"]
    for column in numeric_columns:
        values = pd.to_numeric(report[column], errors="coerce")
        if values.isna().any() or not values.map(math.isfinite).all():
            raise ValueError(
                f"ARTIFACT_CONTRACT_FAILURE: candidate trades contain invalid {column}"
            )
        report[column] = values
    for column in ["Entry Time", "Exit Time"]:
        if pd.to_datetime(report[column], errors="coerce").isna().any():
            raise ValueError(
                f"ARTIFACT_CONTRACT_FAILURE: candidate trades contain invalid {column}"
            )
    duplicate_keys = ["Candidate ID", "Strategy ID", "Pair", "Timeframe", "Trade ID"]
    if report.duplicated(subset=duplicate_keys).any():
        raise ValueError("ARTIFACT_CONTRACT_FAILURE: duplicate candidate trade IDs")
    return report


def _candidate_input(item: dict, trades: pd.DataFrame) -> tuple[str, str, MonteCarloInput]:
    strategy_id = str(item.get("strategy_id", "")).strip()
    if not strategy_id:
        raise ValueError("ARTIFACT_CONTRACT_FAILURE: shortlist strategy_id is missing")
    candidate_id = str(item.get("candidate_id") or strategy_id)
    pairs = list(item.get("recommended_pairs") or [])
    candidate_rows = trades[trades["Strategy ID"].astype(str) == strategy_id]
    if pairs:
        candidate_rows = candidate_rows[candidate_rows["Pair"].isin(pairs)]
    if candidate_rows.empty:
        raise ValueError(
            f"ARTIFACT_CONTRACT_FAILURE: no real trades for candidate {candidate_id}"
        )
    identities = candidate_rows[["Candidate ID", "Strategy ID"]].drop_duplicates()
    if len(identities) != 1 or str(identities.iloc[0]["Candidate ID"]) != candidate_id:
        raise ValueError(
            f"ARTIFACT_CONTRACT_FAILURE: candidate identity mismatch for {candidate_id}"
        )
    initial_values = pd.to_numeric(candidate_rows["Initial Balance"], errors="coerce").dropna()
    if initial_values.empty or not math.isfinite(float(initial_values.iloc[0])):
        raise ValueError(
            f"ARTIFACT_CONTRACT_FAILURE: initial balance missing for {candidate_id}"
        )
    pair = str(candidate_rows.iloc[0]["Pair"])
    timeframe = str(candidate_rows.iloc[0]["Timeframe"])
    mc_input = MonteCarloInput(
        strategy_id=strategy_id,
        strategy_name=str(item.get("name") or strategy_id),
        pair=pair,
        template_type=str(item.get("template_type") or "generated"),
        initial_balance=float(initial_values.iloc[0]),
        trade_returns=candidate_rows["PnL %"].tolist(),
        trade_pnls=candidate_rows["PnL"].tolist(),
        fees=candidate_rows["Fees"].tolist(),
        original_metrics=dict(item.get("minimum_expected_metrics") or {}),
        metadata={"candidate_id": candidate_id, "timeframe": timeframe, "real_trades": True},
    )
    return candidate_id, timeframe, mc_input


def run_monte_carlo_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    output_report = context.run_directory() / "monte_carlo_results.csv"
    summary_path = context.run_directory() / "monte_carlo_summary.json"
    shortlist_path = artifact_path_from_state(state, "robustness_shortlist")
    if not shortlist_path:
        return blocked_payload(
            stage.name,
            "ARTIFACT_CONTRACT_FAILURE: robustness shortlist artifact is missing",
            FAILURE_ARTIFACT,
        )
    try:
        shortlist = _load_shortlist(shortlist_path)
        if not shortlist:
            save_csv_report(pd.DataFrame(columns=MONTE_CARLO_RESULT_COLUMNS), str(output_report))
            save_json_report({"schema_version": "1", "candidates": []}, str(summary_path))
            return stage_payload(
                stage.name,
                "Monte Carlo completed with empty robustness shortlist",
                artifacts=[
                    make_artifact(output_report, "monte_carlo_results", stage.name, "CSV", metadata={"contract_version": "2"}),
                    make_artifact(summary_path, "monte_carlo_summary", stage.name, "JSON", metadata={"contract_version": "2"}),
                ],
                metrics={"candidate_count": 0, "simulation_count": 0},
                warnings=["No robustness-approved candidates available for Monte Carlo"],
            )
        trades_path = artifact_path_from_state(state, "candidate_trades")
        if not trades_path:
            raise ValueError("ARTIFACT_CONTRACT_FAILURE: candidate trades artifact is missing")
        trades = _load_candidate_trades(trades_path)
        simulations = int(benchmark.get("monte_carlo_simulations", 20))
        if benchmark.get("mode") == "SMALL_BENCHMARK":
            simulations = min(simulations, 20)
        reports = []
        summaries = []
        work_directory = context.run_directory() / "monte_carlo_candidates"
        work_directory.mkdir(parents=True, exist_ok=True)
        for item in shortlist:
            candidate_id, timeframe, mc_input = _candidate_input(item, trades)
            candidate_report = work_directory / f"{candidate_id}_results.csv"
            candidate_summary = work_directory / f"{candidate_id}_summary.json"
            report, summary = run_monte_carlo_validation(mc_input, {
                "enabled": True,
                "simulation_count": simulations,
                "random_seed": int(benchmark.get("random_seed", context.random_seed)),
                "output_report": str(candidate_report),
                "output_summary": str(candidate_summary),
                "minimum_simulation_count": 1,
                "maximum_simulation_count": 10000,
                "minimum_positive_run_rate": 0.0,
                "maximum_ruin_probability": 1.0,
            })
            report.insert(0, "Timeframe", timeframe)
            report.insert(0, "Pair", mc_input.pair)
            report.insert(0, "Strategy ID", mc_input.strategy_id)
            report.insert(0, "Candidate ID", candidate_id)
            reports.append(report)
            summaries.append({
                "Candidate ID": candidate_id,
                "Timeframe": timeframe,
                "Trade Count": mc_input.trade_count(),
                **summary,
            })
        combined = pd.concat(reports, ignore_index=True)
        save_csv_report(combined, str(output_report))
        save_json_report({"schema_version": "1", "candidates": summaries}, str(summary_path))
        return stage_payload(
            stage.name,
            "Monte Carlo validation completed from real candidate trades",
            task_usage=len(combined),
            artifacts=[
                make_artifact(output_report, "monte_carlo_results", stage.name, "CSV", metadata={"contract_version": "2"}),
                make_artifact(summary_path, "monte_carlo_summary", stage.name, "JSON", metadata={"contract_version": "2"}),
            ],
            metrics={"candidate_count": len(summaries), "simulation_count": len(combined)},
        )
    except (OSError, ValueError, TypeError, KeyError, pd.errors.ParserError) as error:
        return blocked_payload(stage.name, str(error), FAILURE_ARTIFACT)
