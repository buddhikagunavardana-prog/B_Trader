import pandas as pd

from src.research.generated_candidate_experiment import (
    _build_summary,
    _prevent_duplicate_strategy_ids,
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
    assert config["generated_candidate_limit"] == 30
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


def test_factory_default_behavior_unchanged():
    assert len(get_strategy_combinations()) == 10


def test_factory_generated_limit():
    assert len(get_generated_strategy_combinations(global_max_candidates=5)) == 5


if __name__ == "__main__":
    test_config_loading()
    test_fixed_strategy_retrieval()
    test_generated_strategy_retrieval_and_limit()
    test_duplicate_prevention()
    test_report_schema_and_source_labels()
    test_comparison_summary()
    test_experiment_disabled_behavior()
    test_factory_default_behavior_unchanged()
    test_factory_generated_limit()
    print("test_generated_candidate_experiment passed")
