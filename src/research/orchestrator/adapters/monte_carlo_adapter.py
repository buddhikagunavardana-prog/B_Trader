from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_runner import run_monte_carlo_validation
from src.research.orchestrator.adapters.adapter_result import (
    benchmark_settings,
    make_artifact,
    stage_payload,
)


def run_monte_carlo_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    output_report = context.run_directory() / "monte_carlo_results.csv"
    summary_path = context.run_directory() / "monte_carlo_summary.json"
    simulations = int(benchmark.get("monte_carlo_simulations", 20))
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        simulations = min(simulations, 20)
    mc_input = MonteCarloInput(
        strategy_id="INTEGRATION_CANDIDATE",
        strategy_name="Integration Candidate",
        pair="BTCUSDT",
        template_type="integration",
        initial_balance=10000,
        trade_returns=[1.0, -0.5, 1.25, -0.75, 0.6],
        trade_pnls=[100, -50, 125, -75, 60],
        fees=[1.0] * 5,
    )
    report, summary = run_monte_carlo_validation(mc_input, {
        "enabled": True,
        "simulation_count": simulations,
        "random_seed": int(benchmark.get("random_seed", context.random_seed)),
        "output_report": str(output_report),
        "output_summary": str(summary_path),
        "minimum_simulation_count": 1,
        "maximum_simulation_count": 10000,
        "minimum_positive_run_rate": 0.0,
        "maximum_ruin_probability": 1.0,
    })
    return stage_payload(
        stage.name,
        "Monte Carlo validation completed",
        task_usage=len(report),
        artifacts=[
            make_artifact(output_report, "monte_carlo_results", stage.name, "CSV"),
            make_artifact(summary_path, "monte_carlo_summary", stage.name, "JSON"),
        ],
        metrics=summary,
    )
