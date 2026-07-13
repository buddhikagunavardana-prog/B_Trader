import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.research.benchmark.benchmark_context import build_benchmark_context
from src.research.benchmark.benchmark_preflight import READY, run_preflight_checks
from src.research.orchestrator.adapters.adapter_result import (
    classify_failure,
    make_artifact,
    stage_payload,
)
from src.research.orchestrator.adapters import generated_candidate_adapter
from src.research.orchestrator.adapters import optimization_search_adapter
from src.research.orchestrator.adapters import parameter_optimization_adapter
from src.research.orchestrator.adapters import portfolio_adapter
from src.research.orchestrator.adapters import robustness_adapter
from src.research.orchestrator.adapters import walk_forward_adapter
from src.research.orchestrator.adapters import best_selector_adapter
from src.research.orchestrator.adapters import final_summary_adapter
from src.research.orchestrator.adapters import monte_carlo_adapter
from src.research.orchestrator.adapters.load_data_adapter import _validate_ohlcv
from src.research.orchestrator.orchestrator_registry import (
    PRODUCTION,
    SMOKE,
    build_default_stage_registry,
)
from src.research.orchestrator.orchestrator_stage import OrchestratorStage


class FakeContext:
    run_id = "fake_run"
    random_seed = 42
    metadata = {
        "adapter_mode": "PRODUCTION",
        "benchmark": {
            "mode": "SMALL_BENCHMARK",
            "pairs": ["BTCUSDT"],
            "timeframes": ["15m"],
            "random_seed": 42,
            "generated_candidate_limit": 2,
            "optimization_candidate_budget": 3,
            "walk_forward_windows": 2,
            "robustness_top_candidate_count": 2,
            "portfolio_max_strategies": 2,
            "monte_carlo_simulations": 20,
        },
    }

    def __init__(self, directory: str):
        self.directory = Path(directory)

    def run_directory(self):
        path = self.directory / self.run_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class FakeState:
    def __init__(self):
        self.artifact_manifest = []
        self.completed_stages = []
        self.failed_stages = []
        self.blocked_stages = []


def _stage(name: str):
    return OrchestratorStage(name=name, display_name=name)


def _add_artifact(state, path: Path, name: str, stage_name: str = "source"):
    artifact_type = "JSON" if path.suffix == ".json" else "CSV"
    artifact = make_artifact(path, name, stage_name, artifact_type)
    state.artifact_manifest.append(artifact)
    return artifact


def test_registry_modes_and_no_smoke_in_production():
    smoke = build_default_stage_registry(SMOKE)
    production = build_default_stage_registry(PRODUCTION)

    assert smoke["load_data"].metadata["adapter_mode"] == SMOKE
    assert production["load_data"].metadata["adapter_mode"] == PRODUCTION
    assert "smoke_adapter" not in production["load_data"].runner.__module__


def test_missing_production_adapter_blocks_preflight():
    context = build_benchmark_context({
        "enabled": True,
        "mode": "SMALL_BENCHMARK",
        "pairs": ["BTCUSDT"],
        "timeframes": ["15m"],
    })
    coverage = pd.DataFrame([{
        "Pair": "BTCUSDT",
        "Timeframe": "15m",
        "Coverage Status": "OK",
    }])

    assert run_preflight_checks(context, coverage)["status"] == READY


def test_load_data_adapter_schema_validation():
    valid = pd.DataFrame([{
        "open_time": "2026-01-01",
        "open": 1,
        "high": 2,
        "low": 1,
        "close": 1.5,
        "volume": 10,
    }])
    _validate_ohlcv(valid)

    try:
        _validate_ohlcv(pd.DataFrame([{"open": 1}]))
    except ValueError as error:
        assert "schema" in str(error).lower()
    else:
        raise AssertionError("Invalid OHLCV schema did not fail")


def test_generated_candidate_adapter_contract():
    original = generated_candidate_adapter.generated_candidate_experiment.run_generated_candidate_experiment

    def fake_runner(config):
        Path(config["output_report"]).parent.mkdir(parents=True, exist_ok=True)
        report = pd.DataFrame([{
            "Strategy ID": "G1",
            "Strategy Name": "Generated 1",
            "Strategy Source": "GENERATED",
            "Template Type": "trend",
            "Pair": "BTCUSDT",
            "SL %": 1,
            "TP %": 2,
            "ROI %": 1.0,
            "Profit Factor": 1.2,
            "Win Rate %": 55,
            "Max Drawdown %": -5,
            "Trades": 30,
            "Overall Score": 70,
        }])
        report.to_csv(config["output_report"], index=False)
        Path(config["summary_report"]).write_text("{}", encoding="utf-8")
        return report, {"generated_count": 1, "fixed_count": 0}

    with TemporaryDirectory() as directory:
        generated_candidate_adapter.generated_candidate_experiment.run_generated_candidate_experiment = fake_runner
        payload = generated_candidate_adapter.run_generated_candidate_stage(
            FakeContext(directory),
            _stage("generated_candidate_research"),
            FakeState(),
        )
        generated_candidate_adapter.generated_candidate_experiment.run_generated_candidate_experiment = original

    assert payload["metadata"]["adapter_result"]["status"] == "COMPLETED"
    assert payload["metadata"]["adapter_result"]["metrics"]["generated_count"] == 1


def test_optimization_search_adapter_contract_and_budget_propagation():
    original = optimization_search_adapter.run_parameter_optimizer

    def fake_optimizer(config):
        pd.DataFrame([{"Candidate ID": "C1"}]).to_csv(config["output_report"], index=False)
        Path(config["search_metadata_report"]).write_text("{}", encoding="utf-8")
        return pd.DataFrame([{"Candidate ID": "C1"}]), ["C1", "C2", "C3"]

    with TemporaryDirectory() as directory:
        optimization_search_adapter.run_parameter_optimizer = fake_optimizer
        payload = optimization_search_adapter.run_optimization_search_stage(
            FakeContext(directory),
            _stage("optimization_search"),
            FakeState(),
        )
        optimization_search_adapter.run_parameter_optimizer = original

    assert payload["task_usage"] == 3


def test_parameter_optimization_and_walk_forward_contracts():
    with TemporaryDirectory() as directory:
        context = FakeContext(directory)
        state = FakeState()
        candidates = context.run_directory() / "optimizer_candidates.csv"
        pd.DataFrame([{"Candidate ID": "C1"}]).to_csv(candidates, index=False)
        _add_artifact(state, candidates, "selected_optimizer_candidates")
        opt_payload = parameter_optimization_adapter.run_parameter_optimization_stage(
            context,
            _stage("parameter_optimization"),
            state,
        )
        state.artifact_manifest.extend(opt_payload["artifacts"])
        generated = context.run_directory() / "generated_candidate_comparison.csv"
        pd.DataFrame([{"Strategy ID": "G1", "Strategy Name": "G1", "Pair": "BTCUSDT"}]).to_csv(generated, index=False)
        _add_artifact(state, generated, "generated_candidate_results")
        wf_payload = walk_forward_adapter.run_walk_forward_stage(
            context,
            _stage("walk_forward"),
            state,
        )

    assert opt_payload["metadata"]["adapter_result"]["metrics"]["candidate_count"] == 1
    assert wf_payload["metadata"]["adapter_result"]["metrics"]["rows"] == 1


def test_robustness_empty_shortlist_and_portfolio_no_valid_contracts():
    original = robustness_adapter.run_generated_strategy_robustness

    def fake_robustness(config):
        report = pd.DataFrame(columns=["Strategy ID", "Status"])
        report.to_csv(config["output_report"], index=False)
        Path(config["shortlist_report"]).write_text("[]", encoding="utf-8")
        return report, []

    with TemporaryDirectory() as directory:
        context = FakeContext(directory)
        state = FakeState()
        comparison = context.run_directory() / "generated_candidate_comparison.csv"
        pd.DataFrame([{"Strategy ID": "G1", "Strategy Source": "GENERATED"}]).to_csv(comparison, index=False)
        _add_artifact(state, comparison, "generated_candidate_results")
        robustness_adapter.run_generated_strategy_robustness = fake_robustness
        robust_payload = robustness_adapter.run_robustness_stage(
            context,
            _stage("robustness_validation"),
            state,
        )
        robustness_adapter.run_generated_strategy_robustness = original
        state.artifact_manifest.extend(robust_payload["artifacts"])
        portfolio_payload = portfolio_adapter.run_portfolio_stage(
            context,
            _stage("portfolio_builder"),
            state,
        )

    assert robust_payload["metadata"]["adapter_result"]["metrics"]["shortlist_count"] == 0
    assert "No robustness shortlist" in portfolio_payload["metadata"]["adapter_result"]["warnings"][0]


def test_best_selector_and_final_summary_empty_outputs():
    with TemporaryDirectory() as directory:
        context = FakeContext(directory)
        state = FakeState()
        robustness = context.run_directory() / "generated_strategy_shortlist.json"
        monte_carlo = context.run_directory() / "monte_carlo_summary.json"
        robustness.write_text("[]", encoding="utf-8")
        monte_carlo.write_text('{"schema_version":"1","candidates":[]}', encoding="utf-8")
        _add_artifact(state, robustness, "robustness_shortlist")
        _add_artifact(state, monte_carlo, "monte_carlo_summary")
        best_payload = best_selector_adapter.run_best_selector_stage(
            context,
            _stage("best_strategy_selection"),
            state,
        )
        state.artifact_manifest.extend(best_payload["artifacts"])
        final_payload = final_summary_adapter.run_final_summary_stage(
            context,
            _stage("final_summary"),
            state,
        )

    assert best_payload["metadata"]["adapter_result"]["metrics"]["paper_ready_count"] == 0
    assert final_payload["metadata"]["adapter_result"]["metrics"]["paper_trading_ready"] is False


def test_real_candidate_trades_feed_monte_carlo_and_selector():
    with TemporaryDirectory() as directory:
        context = FakeContext(directory)
        state = FakeState()
        robustness = context.run_directory() / "generated_strategy_shortlist.json"
        robustness.write_text(
            '[{"strategy_id":"G1","name":"Generated 1","template_type":"trend",'
            '"recommended_pairs":["BTCUSDT"],"recommended_regimes":["TRENDING"],'
            '"robustness_score":70,"overfitting_risk_score":25,'
            '"walk_forward_score":72,"walk_forward_pass_rate":0.7,'
            '"pair_consistency_score":65,"regime_consistency_score":60,'
            '"minimum_expected_metrics":{"profit_factor":1.3,"roi_pct":8,'
            '"max_drawdown_pct":-10,"trades":3,"expectancy":10}}]',
            encoding="utf-8",
        )
        trades = context.run_directory() / "candidate_trades.csv"
        pd.DataFrame([
            {
                "Candidate ID": "G1", "Strategy ID": "G1", "Strategy Name": "Generated 1",
                "Template Type": "trend", "Pair": "BTCUSDT", "Timeframe": "15m",
                "Trade ID": index + 1, "Entry Time": f"2026-01-0{index + 1}",
                "Exit Time": f"2026-01-0{index + 2}", "PnL": pnl, "PnL %": pnl / 100,
                "Fees": 1.0, "Initial Balance": 10000 if index == 0 else None,
            }
            for index, pnl in enumerate([100, -50, 125])
        ]).to_csv(trades, index=False)
        _add_artifact(state, robustness, "robustness_shortlist")
        _add_artifact(state, trades, "candidate_trades")
        mc_payload = monte_carlo_adapter.run_monte_carlo_stage(
            context, _stage("monte_carlo"), state,
        )
        state.artifact_manifest.extend(mc_payload["artifacts"])
        best_payload = best_selector_adapter.run_best_selector_stage(
            context, _stage("best_strategy_selection"), state,
        )

        summary = pd.read_json(context.run_directory() / "monte_carlo_summary.json")
        ranking = pd.read_csv(context.run_directory() / "final_benchmark_ranking.csv")
        with open(
            context.run_directory() / "final_candidate_metrics.json",
            encoding="utf-8",
        ) as file:
            final_metrics = json.load(file)

    assert mc_payload["metadata"]["adapter_result"]["status"] == "COMPLETED"
    assert mc_payload["metadata"]["adapter_result"]["metrics"]["candidate_count"] == 1
    assert best_payload["metadata"]["adapter_result"]["metrics"]["candidate_count"] == 1
    assert ranking.iloc[0]["Candidate ID"] == "G1"
    assert final_metrics[0]["Walk Forward Pass Rate"] == 0.7
    assert final_metrics[0]["Overfitting Risk"] == 25
    assert final_metrics[0]["Monte Carlo Positive Run Rate"] >= 0
    assert "INTEGRATION_CANDIDATE" not in summary.to_json()


def test_monte_carlo_missing_or_malformed_trade_contract_is_blocked():
    with TemporaryDirectory() as directory:
        context = FakeContext(directory)
        state = FakeState()
        robustness = context.run_directory() / "generated_strategy_shortlist.json"
        robustness.write_text('[{"strategy_id":"G1"}]', encoding="utf-8")
        _add_artifact(state, robustness, "robustness_shortlist")
        missing = monte_carlo_adapter.run_monte_carlo_stage(
            context, _stage("monte_carlo"), state,
        )
        trades = context.run_directory() / "candidate_trades.csv"
        pd.DataFrame([{"Candidate ID": "G1", "Strategy ID": "G1", "PnL": float("inf")}]).to_csv(trades, index=False)
        _add_artifact(state, trades, "candidate_trades")
        malformed = monte_carlo_adapter.run_monte_carlo_stage(
            context, _stage("monte_carlo"), state,
        )

    assert missing["metadata"]["adapter_result"]["status"] == "BLOCKED"
    assert malformed["metadata"]["adapter_result"]["status"] == "BLOCKED"
    assert "ARTIFACT_CONTRACT_FAILURE" in malformed["message"]


def test_failure_classification_and_adapter_result_contract():
    assert classify_failure(RuntimeError("SSL certificate failed")) == "BINANCE_SSL_FAILURE"
    payload = stage_payload("unit", "ok", metrics={"x": 1})
    result = payload["metadata"]["adapter_result"]

    assert result["stage_name"] == "unit"
    assert result["success"] is True
    assert result["metrics"]["x"] == 1


def test_backward_compatible_default_registry_is_smoke():
    registry = build_default_stage_registry()

    assert registry["load_data"].metadata["adapter_mode"] == SMOKE


if __name__ == "__main__":
    test_registry_modes_and_no_smoke_in_production()
    test_missing_production_adapter_blocks_preflight()
    test_load_data_adapter_schema_validation()
    test_generated_candidate_adapter_contract()
    test_optimization_search_adapter_contract_and_budget_propagation()
    test_parameter_optimization_and_walk_forward_contracts()
    test_robustness_empty_shortlist_and_portfolio_no_valid_contracts()
    test_best_selector_and_final_summary_empty_outputs()
    test_real_candidate_trades_feed_monte_carlo_and_selector()
    test_monte_carlo_missing_or_malformed_trade_contract_is_blocked()
    test_failure_classification_and_adapter_result_contract()
    test_backward_compatible_default_registry_is_smoke()
    print("test_production_adapters passed")
