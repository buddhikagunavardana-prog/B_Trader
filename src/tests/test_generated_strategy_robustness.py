import pandas as pd
from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.generated_strategy_robustness import (
    REPORT_COLUMNS,
    calculate_overfitting_risk,
    calculate_historical_regime_consistency,
    calculate_pair_consistency,
    calculate_regime_consistency,
    calculate_robustness_score,
    determine_status,
    generate_neighbor_parameters,
    load_robustness_config,
    run_generated_strategy_robustness,
    select_top_generated_candidates,
)


def _sample_comparison_report() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Strategy ID": "GEN_1",
            "Strategy Name": "Generated One",
            "Strategy Source": "GENERATED",
            "Template Type": "trend",
            "Pair": "BTCUSDT",
            "SL %": 1.0,
            "TP %": 2.0,
            "ROI %": 20.0,
            "Profit Factor": 1.4,
            "Win Rate %": 52.0,
            "Max Drawdown %": -12.0,
            "Trades": 80,
            "Overall Score": 75.0,
        },
        {
            "Strategy ID": "GEN_1",
            "Strategy Name": "Generated One",
            "Strategy Source": "GENERATED",
            "Template Type": "trend",
            "Pair": "ETHUSDT",
            "SL %": 1.0,
            "TP %": 2.0,
            "ROI %": 12.0,
            "Profit Factor": 1.2,
            "Win Rate %": 49.0,
            "Max Drawdown %": -14.0,
            "Trades": 55,
            "Overall Score": 68.0,
        },
        {
            "Strategy ID": "GEN_2",
            "Strategy Name": "Generated Two",
            "Strategy Source": "GENERATED",
            "Template Type": "hybrid",
            "Pair": "BTCUSDT",
            "SL %": 1.5,
            "TP %": 3.0,
            "ROI %": 5.0,
            "Profit Factor": 1.0,
            "Win Rate %": 40.0,
            "Max Drawdown %": -38.0,
            "Trades": 20,
            "Overall Score": 40.0,
        },
        {
            "Strategy ID": "FIXED_1",
            "Strategy Name": "Fixed One",
            "Strategy Source": "FIXED",
            "Template Type": "fixed",
            "Pair": "BTCUSDT",
            "SL %": 1.0,
            "TP %": 2.0,
            "ROI %": 30.0,
            "Profit Factor": 1.6,
            "Win Rate %": 55.0,
            "Max Drawdown %": -10.0,
            "Trades": 100,
            "Overall Score": 90.0,
        },
    ])


def _sample_config() -> dict:
    return {
        "minimum_trades": 30,
        "minimum_profit_factor": 1.05,
        "maximum_drawdown_pct": 35.0,
        "historical_regime_minimum_trades": 2,
        "maximum_neighbor_degradation_pct": 30.0,
        "pass_score": 65.0,
    }


def test_config_loading_disabled_by_default():
    config = load_robustness_config()

    assert config["enabled"] is False
    assert config["top_candidate_count"] == 10
    assert config["neighbor_limit"] == 8


def test_top_selection_uses_generated_only_and_unique_ids():
    top = select_top_generated_candidates(_sample_comparison_report(), 2)

    assert list(top["Strategy ID"]) == ["GEN_1", "GEN_2"]
    assert "FIXED_1" not in set(top["Strategy ID"])


def test_top_selection_can_be_limited_to_smoke_pair():
    top = select_top_generated_candidates(
        _sample_comparison_report(),
        3,
        pairs=["ETHUSDT"],
    )

    assert len(top) == 1
    assert top.iloc[0]["Strategy ID"] == "GEN_1"
    assert top.iloc[0]["Pair"] == "ETHUSDT"


def test_pair_consistency_scores_profitable_pairs():
    report = _sample_comparison_report()
    strategy_rows = report[report["Strategy ID"] == "GEN_1"]
    result = calculate_pair_consistency(strategy_rows, _sample_config())

    assert result["score"] > 70
    assert result["recommended_pairs"] == ["BTCUSDT", "ETHUSDT"]


def test_regime_consistency_uses_pair_regime_map():
    report = _sample_comparison_report()
    strategy_rows = report[report["Strategy ID"] == "GEN_1"]
    result = calculate_regime_consistency(
        strategy_rows,
        {"BTCUSDT": "TRENDING", "ETHUSDT": "SIDEWAYS"},
        _sample_config(),
    )

    assert result["score"] > 60
    assert set(result["recommended_regimes"]) == {"TRENDING", "SIDEWAYS"}


def test_historical_regime_consistency_uses_real_trade_outcomes():
    trades = pd.DataFrame({
        "Entry Time": pd.to_datetime([
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:15:00Z",
            "2025-01-01T00:30:00Z",
            "2025-01-01T00:45:00Z",
            "2025-01-01T01:00:00Z",
        ]),
        "PnL": [100.0, -20.0, 50.0, -10.0, 5.0],
        "Initial Balance": [1000.0, None, None, None, None],
    })
    regimes = pd.DataFrame({
        "open_time": trades["Entry Time"],
        "Regime": [
            "TRENDING",
            "TRENDING",
            "SIDEWAYS",
            "SIDEWAYS",
            "HIGH_VOLATILITY",
        ],
    })

    result = calculate_historical_regime_consistency(
        trades,
        regimes,
        _sample_config(),
    )

    assert result["method"] == "HISTORICAL_PRIOR_CANDLE"
    assert result["regime_count"] == 2
    assert result["observed_regime_count"] == 3
    assert set(result["recommended_regimes"]) == {"TRENDING", "SIDEWAYS"}
    assert len(result["details"]) == 3
    assert sum(item["sample_sufficient"] for item in result["details"]) == 2


def test_neighbor_generation_is_limited_and_valid():
    neighbors = generate_neighbor_parameters(
        {
            "template_id": "TRD001",
            "timeframe": "15m",
            "fast_ema": 20,
            "slow_ema": 100,
            "rsi_period": 14,
            "rsi_pullback": 40,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 2.0,
        },
        4,
    )

    assert len(neighbors) == 4
    assert all(item["fast_ema"] < item["slow_ema"] for item in neighbors)


def test_score_outputs_are_bounded():
    walk_forward = {"pass_rate": 80.0, "average_score": 75.0}
    pair = {"score": 85.0}
    regime = {"score": 70.0}
    parameter = {"score": 90.0}
    original = pd.Series({
        "Profit Factor": 1.4,
        "Max Drawdown %": -12.0,
        "Trades": 80,
    })
    config = _sample_config()

    robustness = calculate_robustness_score(
        walk_forward,
        pair,
        regime,
        parameter,
        original,
        config,
    )
    risk = calculate_overfitting_risk(
        walk_forward,
        pair,
        regime,
        parameter,
        original,
        config,
    )

    assert 0 <= robustness <= 100
    assert 0 <= risk <= 100


def test_status_rejects_low_walk_forward_pass_rate():
    status, reasons = determine_status(
        robustness_score=70,
        overfitting_risk_score=45,
        walk_forward_result={"pass_rate": 25},
        pair_result={"score": 80},
        parameter_result={"score": 80},
        original_row=pd.Series({
            "Profit Factor": 1.3,
            "Trades": 100,
            "Max Drawdown %": -10,
        }),
        config=_sample_config(),
    )

    assert status in {"FRAGILE", "REJECTED"}
    assert "Walk-forward pass rate below 50%" in reasons


def test_disabled_run_returns_empty_report_schema():
    report, shortlist = run_generated_strategy_robustness({"enabled": False})

    assert list(report.columns) == REPORT_COLUMNS
    assert shortlist == []


def test_fixed_only_survivor_artifact_returns_valid_empty_shortlist():
    survivor = _sample_comparison_report().query(
        "`Strategy Source` == 'FIXED'"
    )
    with TemporaryDirectory() as directory:
        comparison = Path(directory, "funnel_1y_survivors.csv")
        output = Path(directory, "robustness.csv")
        shortlist_path = Path(directory, "shortlist.json")
        survivor.to_csv(comparison, index=False)
        report, shortlist = run_generated_strategy_robustness({
            "enabled": True,
            "comparison_report": str(comparison),
            "output_report": str(output),
            "shortlist_report": str(shortlist_path),
            "pairs": ["BTCUSDT"],
        })

        assert list(report.columns) == REPORT_COLUMNS
        assert report.empty
        assert shortlist == []
        assert pd.read_csv(output).empty
        assert shortlist_path.read_text(encoding="utf-8").strip() == "[]"


if __name__ == "__main__":
    test_config_loading_disabled_by_default()
    test_top_selection_uses_generated_only_and_unique_ids()
    test_top_selection_can_be_limited_to_smoke_pair()
    test_pair_consistency_scores_profitable_pairs()
    test_regime_consistency_uses_pair_regime_map()
    test_historical_regime_consistency_uses_real_trade_outcomes()
    test_neighbor_generation_is_limited_and_valid()
    test_score_outputs_are_bounded()
    test_status_rejects_low_walk_forward_pass_rate()
    test_disabled_run_returns_empty_report_schema()
    test_fixed_only_survivor_artifact_returns_valid_empty_shortlist()
    print("test_generated_strategy_robustness passed")
