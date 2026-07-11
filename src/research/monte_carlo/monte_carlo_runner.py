import pandas as pd

from src.research.monte_carlo.monte_carlo_constraints import (
    evaluate_monte_carlo_constraints,
)
from src.research.monte_carlo.monte_carlo_context import build_monte_carlo_context
from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_metrics import aggregate_monte_carlo_metrics
from src.research.monte_carlo.monte_carlo_report import (
    build_summary,
    results_to_report,
    save_monte_carlo_report,
    save_monte_carlo_summary,
)
from src.research.monte_carlo.monte_carlo_sampler import MonteCarloSampler
from src.research.monte_carlo.monte_carlo_simulator import run_simulations


def run_monte_carlo_validation(
    mc_input: MonteCarloInput | None = None,
    config_override: dict | None = None,
):
    context = build_monte_carlo_context(config_override)

    if not context.enabled:
        print("Monte Carlo validation disabled by config.")
        return pd.DataFrame(), {}

    if mc_input is None:
        raise ValueError("Monte Carlo validation requires prepared input")

    sampler = MonteCarloSampler(context)
    scenarios = sampler.generate_scenarios(mc_input)
    results = run_simulations(mc_input, scenarios)
    metrics = aggregate_monte_carlo_metrics(results, context)
    constraint_result = evaluate_monte_carlo_constraints(metrics, context)
    summary = build_summary(mc_input, metrics, constraint_result)

    if context.output_report:
        report = save_monte_carlo_report(results, context.output_report)
    else:
        report = results_to_report(results)

    if context.output_summary:
        save_monte_carlo_summary(summary, context.output_summary)

    print("\n===== B TRADER MONTE CARLO FOUNDATION =====")
    print(f"Simulation count: {metrics['simulation_count']}")
    print(f"Positive run rate: {metrics['positive_run_rate']}")
    print(f"Ruin probability: {metrics['ruin_probability']}")
    print(f"Median ROI %: {metrics['median_roi_pct']}")
    print(f"Worst drawdown %: {metrics['worst_max_drawdown_pct']}")
    print(f"Stability score: {metrics['stability_score']}")

    return report, summary


if __name__ == "__main__":
    run_monte_carlo_validation()
