from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.monte_carlo.monte_carlo_constraints import (
    evaluate_monte_carlo_constraints,
)
from src.research.monte_carlo.monte_carlo_context import (
    build_monte_carlo_context,
    load_monte_carlo_config,
)
from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_metrics import (
    aggregate_monte_carlo_metrics,
)
from src.research.monte_carlo.monte_carlo_report import (
    build_summary,
    results_to_report,
    save_monte_carlo_report,
    save_monte_carlo_summary,
)
from src.research.monte_carlo.monte_carlo_runner import run_monte_carlo_validation
from src.research.monte_carlo.monte_carlo_sampler import (
    MonteCarloSampler,
    validate_sampler_config,
)
from src.research.monte_carlo.monte_carlo_simulator import (
    calculate_max_drawdown_pct,
    run_simulations,
    simulate_scenario,
)
from src.research.pipeline.pipeline_context import PipelineContext


def _context(**overrides):
    config = {
        "enabled": True,
        "simulation_count": 5,
        "random_seed": 42,
        "confidence_levels": [0.05, 0.25, 0.5, 0.75, 0.95],
        "shuffle_trade_order": True,
        "sample_with_replacement": True,
        "slippage_enabled": True,
        "slippage_range_pct": [-0.05, 0.05],
        "fee_perturbation_enabled": True,
        "fee_range_pct": [-0.02, 0.02],
        "missed_trade_enabled": True,
        "missed_trade_probability": 0.1,
        "return_noise_enabled": True,
        "return_noise_std_pct": 0.05,
        "maximum_drawdown_limit_pct": 30.0,
        "minimum_positive_run_rate": 0.5,
        "maximum_ruin_probability": 0.2,
        "minimum_simulation_count": 1,
        "maximum_simulation_count": 20,
        "minimum_median_roi_pct": -100.0,
        "minimum_successful_simulation_ratio": 0.9,
        "output_report": None,
        "output_summary": None,
    }
    config.update(overrides)
    return build_monte_carlo_context(config)


def _input(**overrides):
    config = {
        "strategy_id": "STRAT_A",
        "strategy_name": "Strategy A",
        "pair": "BTCUSDT",
        "template_type": "trend",
        "initial_balance": 10000.0,
        "trade_returns": [1.0, -0.5, 1.5, -1.0, 0.75],
        "trade_pnls": [100.0, -50.0, 150.0, -100.0, 75.0],
        "fees": [1.0, 1.0, 1.0, 1.0, 1.0],
    }
    config.update(overrides)
    return MonteCarloInput(**config)


def test_config_loading_disabled_by_default():
    config = load_monte_carlo_config()

    assert config["enabled"] is False
    assert config["random_seed"] == 42


def test_context_pipeline_compatibility():
    pipeline_context = _context().to_pipeline_context()

    assert isinstance(pipeline_context, PipelineContext)
    assert pipeline_context.name == "monte_carlo_validation"


def test_disabled_behavior():
    report, summary = run_monte_carlo_validation(config_override={"enabled": False})

    assert report.empty
    assert summary == {}


def test_input_validation_rejects_empty_and_non_finite():
    try:
        _input(trade_returns=[], trade_pnls=[])
    except ValueError as error:
        assert "requires trade_returns or trade_pnls" in str(error)
    else:
        raise AssertionError("Empty input did not fail")

    try:
        _input(trade_returns=[float("inf")], trade_pnls=[])
    except ValueError as error:
        assert "non-finite" in str(error)
    else:
        raise AssertionError("Non-finite input did not fail")


def test_input_validation_lengths_and_initial_balance():
    try:
        _input(initial_balance=-1)
    except ValueError as error:
        assert "initial_balance" in str(error)
    else:
        raise AssertionError("Negative balance did not fail")

    try:
        _input(trade_returns=[1, 2], trade_pnls=[1])
    except ValueError as error:
        assert "lengths must match" in str(error)
    else:
        raise AssertionError("Mismatched lengths did not fail")


def test_deterministic_same_seed_scenarios():
    sampler = MonteCarloSampler(_context())
    first = [scenario.to_dict() for scenario in sampler.generate_scenarios(_input())]
    second = [scenario.to_dict() for scenario in sampler.generate_scenarios(_input())]

    assert first == second


def test_different_seed_changes_scenario():
    first = MonteCarloSampler(_context(random_seed=42)).generate_scenarios(_input())[0]
    second = MonteCarloSampler(_context(random_seed=7)).generate_scenarios(_input())[0]

    assert first.to_dict() != second.to_dict()


def test_sampler_features_and_bounds():
    context = _context(simulation_count=1)
    scenario = MonteCarloSampler(context).generate_scenarios(_input())[0]

    assert sorted(scenario.trade_order) == list(range(_input().trade_count()))
    assert len(scenario.sample_indices) == _input().trade_count()
    assert all(-0.05 <= item <= 0.05 for item in scenario.slippage_adjustments)
    assert all(-0.02 <= item <= 0.02 for item in scenario.fee_adjustments)
    assert all(isinstance(item, bool) for item in scenario.missed_trade_mask)
    assert len(scenario.return_noise) == _input().trade_count()


def test_sampler_rejects_invalid_probabilities_and_ranges():
    try:
        validate_sampler_config(_context(missed_trade_probability=1.5))
    except ValueError as error:
        assert "missed_trade_probability" in str(error)
    else:
        raise AssertionError("Invalid probability did not fail")

    try:
        validate_sampler_config(_context(slippage_range_pct=[1, -1]))
    except ValueError as error:
        assert "slippage_range_pct" in str(error)
    else:
        raise AssertionError("Invalid range did not fail")


def test_simulation_does_not_mutate_input_and_calculates_outputs():
    mc_input = _input()
    original = mc_input.to_dict()
    scenario = MonteCarloSampler(_context(simulation_count=1)).generate_scenarios(mc_input)[0]
    result = simulate_scenario(mc_input, scenario)

    assert mc_input.to_dict() == original
    assert result.trade_count >= 0
    assert isinstance(result.final_balance, float)
    assert isinstance(result.roi_pct, float)
    assert result.max_drawdown_pct <= 0


def test_ruin_detection():
    mc_input = _input(
        trade_returns=[-100.0],
        trade_pnls=[-10000.0],
        fees=[0.0],
    )
    scenario = MonteCarloSampler(_context(
        simulation_count=1,
        shuffle_trade_order=False,
        sample_with_replacement=False,
        slippage_enabled=False,
        fee_perturbation_enabled=False,
        missed_trade_enabled=False,
        return_noise_enabled=False,
    )).generate_scenarios(mc_input)[0]
    result = simulate_scenario(mc_input, scenario)

    assert result.ruin is True


def test_drawdown_calculation():
    assert calculate_max_drawdown_pct([100, 120, 90]) == -25.0


def test_metrics_aggregation_and_score_bounds():
    context = _context(simulation_count=5)
    results = run_simulations(
        _input(),
        MonteCarloSampler(context).generate_scenarios(_input()),
    )
    metrics = aggregate_monte_carlo_metrics(results, context)

    assert metrics["simulation_count"] == 5
    assert 0 <= metrics["positive_run_rate"] <= 1
    assert 0 <= metrics["ruin_probability"] <= 1
    assert 0 <= metrics["stability_score"] <= 100
    assert 0 <= metrics["risk_score"] <= 100
    assert "percentile_5_roi_pct" in metrics
    assert "0.5" in metrics["confidence_intervals"]


def test_constraints_pass_fail_and_reasons():
    context = _context(minimum_positive_run_rate=0.0)
    results = run_simulations(
        _input(),
        MonteCarloSampler(context).generate_scenarios(_input()),
    )
    metrics = aggregate_monte_carlo_metrics(results, context)
    passed = evaluate_monte_carlo_constraints(metrics, context)
    failed = evaluate_monte_carlo_constraints(
        {**metrics, "ruin_probability": 1.0},
        context,
    )

    assert passed.status in {"PASS", "FAIL"}
    assert failed.passed is False
    assert "ruin probability above maximum" in failed.reasons


def test_csv_json_schema():
    context = _context(simulation_count=2)
    mc_input = _input()
    results = run_simulations(
        mc_input,
        MonteCarloSampler(context).generate_scenarios(mc_input),
    )
    metrics = aggregate_monte_carlo_metrics(results, context)
    constraint_result = evaluate_monte_carlo_constraints(metrics, context)
    summary = build_summary(mc_input, metrics, constraint_result)
    report = results_to_report(results)

    assert "Simulation Index" in report.columns
    assert "Constraint Status" in summary

    with TemporaryDirectory() as directory:
        csv_path = str(Path(directory) / "mc.csv")
        json_path = str(Path(directory) / "mc.json")
        save_monte_carlo_report(results, csv_path)
        save_monte_carlo_summary(summary, json_path)
        assert Path(csv_path).exists()
        assert Path(json_path).exists()


def test_strategy_and_portfolio_level_inputs():
    strategy_input = _input()
    portfolio_input = _input(
        strategy_id="PORT_A",
        strategy_name="Portfolio A",
        pair="PORTFOLIO",
        template_type="portfolio",
        trade_returns=[0.5, -0.25, 0.75],
        trade_pnls=[],
        fees=[],
        portfolio_weights={"STRAT_A": 0.6, "STRAT_B": 0.4},
    )

    assert strategy_input.trade_count() == 5
    assert portfolio_input.trade_count() == 3
    assert portfolio_input.portfolio_weights["STRAT_A"] == 0.6


def test_runner_small_smoke_with_temp_outputs():
    with TemporaryDirectory() as directory:
        report_path = str(Path(directory) / "mc.csv")
        summary_path = str(Path(directory) / "mc.json")
        report, summary = run_monte_carlo_validation(
            _input(),
            {
                "enabled": True,
                "simulation_count": 5,
                "random_seed": 42,
                "output_report": report_path,
                "output_summary": summary_path,
                "minimum_simulation_count": 1,
                "minimum_positive_run_rate": 0.0,
            },
        )

        assert Path(report_path).exists()
        assert Path(summary_path).exists()

    assert len(report) == 5
    assert summary["Simulation Count"] == 5


if __name__ == "__main__":
    test_config_loading_disabled_by_default()
    test_context_pipeline_compatibility()
    test_disabled_behavior()
    test_input_validation_rejects_empty_and_non_finite()
    test_input_validation_lengths_and_initial_balance()
    test_deterministic_same_seed_scenarios()
    test_different_seed_changes_scenario()
    test_sampler_features_and_bounds()
    test_sampler_rejects_invalid_probabilities_and_ranges()
    test_simulation_does_not_mutate_input_and_calculates_outputs()
    test_ruin_detection()
    test_drawdown_calculation()
    test_metrics_aggregation_and_score_bounds()
    test_constraints_pass_fail_and_reasons()
    test_csv_json_schema()
    test_strategy_and_portfolio_level_inputs()
    test_runner_small_smoke_with_temp_outputs()
    print("test_monte_carlo_foundation passed")
