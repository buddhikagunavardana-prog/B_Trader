import pandas as pd

from src.research.generated_candidate_experiment import (
    _build_summary,
    _prevent_duplicate_strategy_ids,
    _resolve_trade_timestamp,
    _score_report,
    load_experiment_config,
    load_fixed_strategy_records,
    load_generated_strategy_records,
    run_generated_candidate_experiment,
)
from src.strategies.strategy_factory import (
    get_generated_strategy_combinations,
    get_strategy_combinations,
)


def _sample_report(strategy_source: str) -> pd.DataFrame:
    return _score_report(pd.DataFrame([{
        "Strategy ID": f"{strategy_source}_001",
        "Strategy Name": f"{strategy_source} Strategy",
        "Strategy Source": strategy_source,
        "Template Type": "fixed" if strategy_source == "FIXED" else "trend",
        "Pair": "BTCUSDT",
        "Timeframe": "15m",
        "SL %": 1.0,
        "TP %": 2.0,
        "ROI %": 10.0,
        "Profit Factor": 1.2,
        "Total PnL %": 12.0,
        "Win Rate %": 45.0,
        "Max Drawdown %": -12.0,
        "Trades": 50,
        "Expectancy": 2.0,
        "Runtime Seconds": 1.0,
    }]))


def test_config_loading():
    config = load_experiment_config()

    assert config["enabled"] is False
    assert config["generated_candidate_limit"] == 120
    assert config["timeframe"] == "15m"


def test_fixed_strategy_retrieval():
    fixed_records = load_fixed_strategy_records()

    assert len(fixed_records) == 10
    assert all(record["strategy_source"] == "FIXED" for record in fixed_records)


def test_generated_strategy_retrieval_and_limit():
    generated_records = load_generated_strategy_records(7)

    assert len(generated_records) == 7
    assert all(
        record["strategy_source"] == "GENERATED"
        for record in generated_records
    )


def test_generated_strategy_retrieval_includes_configured_atr_variants():
    config = load_experiment_config()
    records = load_generated_strategy_records(60, config["atr_exit_variants"])

    assert len(records) == 60
    assert sum(
        record["strategy"].exit_rules.get("simulated_exit_mode")
        == "atr_full_position"
        for record in records
    ) == 30
    assert len({record["strategy_id"] for record in records}) == 60


def test_generated_strategy_retrieval_includes_risk_sizing_variants():
    config = load_experiment_config()
    records = load_generated_strategy_records(
        120,
        config["atr_exit_variants"],
        config["risk_sizing_variants"],
    )

    assert len(records) == 120
    assert sum(
        record["strategy"].risk.get("position_sizing_mode")
        == "risk_normalized"
        for record in records
    ) == 60
    assert all(
        "RISK1P0_CAP25P0" in record["strategy_id"]
        for record in records[60:]
    )


def test_duplicate_prevention():
    records = [
        {"strategy_id": "DUPLICATE"},
        {"strategy_id": "DUPLICATE"},
    ]

    try:
        _prevent_duplicate_strategy_ids(records)
    except ValueError as error:
        assert "Duplicate strategy ID" in str(error)
    else:
        raise AssertionError("Duplicate IDs did not fail")


def test_report_schema_and_source_labels():
    report = _sample_report("GENERATED")

    expected_columns = {
        "Strategy ID",
        "Strategy Name",
        "Strategy Source",
        "Template Type",
        "Pair",
        "Timeframe",
        "SL %",
        "TP %",
        "ROI %",
        "Profit Factor",
        "Win Rate %",
        "Max Drawdown %",
        "Trades",
        "Expectancy",
        "Overall Score",
        "Runtime Seconds",
    }

    assert expected_columns.issubset(set(report.columns))
    assert report.iloc[0]["Strategy Source"] == "GENERATED"


def test_comparison_summary():
    fixed_report = _sample_report("FIXED")
    generated_report = _sample_report("GENERATED")
    generated_report.loc[0, "ROI %"] = 15.0
    generated_report = _score_report(generated_report)

    summary = _build_summary(
        fixed_report,
        generated_report,
        fixed_runtime=1.0,
        generated_runtime=2.0,
    )

    assert summary["fixed_count"] == 1
    assert summary["generated_count"] == 1
    assert summary["improvement"]["roi_pct"] == 5.0


def test_experiment_disabled_behavior():
    report, summary = run_generated_candidate_experiment({"enabled": False})

    assert report.empty
    assert summary == {}


def test_trade_timestamps_resolve_from_market_calendar():
    market_data = pd.DataFrame({
        "open_time": pd.to_datetime([
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:15:00Z",
        ]),
    })
    trade = {
        "entry_index": 0,
        "exit_index": 1,
        "entry_time": 0,
        "exit_time": 1,
    }

    assert _resolve_trade_timestamp(
        market_data, trade, "entry_time", "entry_index"
    ) == "2025-01-01T00:00:00+00:00"
    assert _resolve_trade_timestamp(
        market_data, trade, "exit_time", "exit_index"
    ) == "2025-01-01T00:15:00+00:00"


def test_factory_default_behavior_unchanged():
    assert len(get_strategy_combinations()) == 10


def test_factory_generated_limit():
    assert len(get_generated_strategy_combinations(global_max_candidates=5)) == 5


if __name__ == "__main__":
    test_config_loading()
    test_fixed_strategy_retrieval()
    test_generated_strategy_retrieval_and_limit()
    test_generated_strategy_retrieval_includes_configured_atr_variants()
    test_generated_strategy_retrieval_includes_risk_sizing_variants()
    test_duplicate_prevention()
    test_report_schema_and_source_labels()
    test_comparison_summary()
    test_experiment_disabled_behavior()
    test_trade_timestamps_resolve_from_market_calendar()
    test_factory_default_behavior_unchanged()
    test_factory_generated_limit()
    print("test_generated_candidate_experiment passed")
