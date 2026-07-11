import pandas as pd

from src.research.monte_carlo.monte_carlo_constraints import (
    MonteCarloConstraintResult,
)
from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_simulator import (
    MonteCarloSimulationResult,
)
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


def results_to_report(
    results: list[MonteCarloSimulationResult],
) -> pd.DataFrame:
    return pd.DataFrame([result.to_report_row() for result in results])


def build_summary(
    mc_input: MonteCarloInput,
    metrics: dict,
    constraint_result: MonteCarloConstraintResult,
) -> dict:
    return {
        "Strategy ID": mc_input.strategy_id,
        "Strategy Name": mc_input.strategy_name,
        "Pair": mc_input.pair,
        "Simulation Count": metrics["simulation_count"],
        "Positive Run Rate": metrics["positive_run_rate"],
        "Ruin Probability": metrics["ruin_probability"],
        "Median ROI %": metrics["median_roi_pct"],
        "Worst ROI %": metrics["worst_roi_pct"],
        "Median Max Drawdown %": metrics["median_max_drawdown_pct"],
        "Worst Max Drawdown %": metrics["worst_max_drawdown_pct"],
        "Stability Score": metrics["stability_score"],
        "Risk Score": metrics["risk_score"],
        "Constraint Status": constraint_result.status,
        "Constraint Reasons": list(constraint_result.reasons),
        "Metrics": metrics,
    }


def save_monte_carlo_report(
    results: list[MonteCarloSimulationResult],
    output_report: str,
) -> pd.DataFrame:
    report = results_to_report(results)
    save_csv_report(report, output_report)

    return report


def save_monte_carlo_summary(summary: dict, output_summary: str) -> dict:
    save_json_report(summary, output_summary)
    return summary
