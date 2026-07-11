from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.research.generated_candidate_experiment import (
    _build_tasks,
    _prevent_duplicate_strategy_ids,
    _score_report,
    load_experiment_config,
    run_generated_candidate_experiment,
)
from src.research.generated_strategy_robustness import (
    run_generated_strategy_robustness,
)
from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_executor import (
    execute_tasks,
    get_worker_market_data,
)
from src.research.pipeline.pipeline_filters import (
    filter_tasks_by_predicate,
    limit_by_task_budget,
    prevent_duplicate_ids,
)
from src.research.pipeline.pipeline_loader import (
    load_csv_report,
    load_json_config,
    load_market_data,
)
from src.research.pipeline.pipeline_metrics import add_research_score_columns
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report
from src.research.pipeline.pipeline_runner import build_strategy_pair_tasks
from src.research.strategy_combination_lab import load_strategy_template_config


def _fake_market_loader(pair: str, timeframe: str, lookback: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "pair": pair,
        "timeframe": timeframe,
        "lookback": lookback,
        "open": 1.0,
        "high": 2.0,
        "low": 0.5,
        "close": 1.5,
        "volume": 100.0,
    }])


def _sample_report() -> pd.DataFrame:
    return pd.DataFrame([{
        "Profit Factor": 1.2,
        "Total PnL %": 10.0,
        "Win Rate %": 45.0,
        "Max Drawdown %": -12.0,
        "Trades": 50,
    }])


def _sample_evaluator(task):
    df = get_worker_market_data(task.pair)
    return {
        "item_index": task.item_index,
        "pair_index": task.pair_index,
        "pair": task.pair,
        "rows": len(df),
        "payload": task.payload["name"],
    }


def test_pipeline_context_creation():
    context = PipelineContext(
        name="unit",
        pairs=["BTCUSDT"],
        timeframe="15m",
        lookback="synthetic",
        output_report="reports/unit.csv",
        max_workers=1,
    )

    assert context.name == "unit"
    assert context.pairs == ["BTCUSDT"]
    assert context.timeframe == "15m"


def test_json_config_loading_with_defaults_and_required_keys():
    with TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text('{"enabled": true}', encoding="utf-8")

        config = load_json_config(
            config_path,
            required_keys=["enabled", "limit"],
            defaults={"limit": 3},
        )

    assert config == {"limit": 3, "enabled": True}


def test_market_data_loader_uses_injected_loader():
    market_data = load_market_data(
        ["BTCUSDT", "ETHUSDT"],
        "15m",
        "synthetic",
        data_loader=_fake_market_loader,
    )

    assert set(market_data) == {"BTCUSDT", "ETHUSDT"}
    assert market_data["BTCUSDT"].iloc[0]["timeframe"] == "15m"


def test_task_generation_and_sequential_execution():
    records = [{"name": "alpha"}, {"name": "beta"}]
    pairs = ["BTCUSDT", "ETHUSDT"]
    tasks = build_strategy_pair_tasks(records, pairs, "15m")
    market_data = {
        pair: _fake_market_loader(pair, "15m", "synthetic")
        for pair in pairs
    }

    rows, failures = execute_tasks(
        tasks,
        _sample_evaluator,
        max_workers=1,
        market_data=market_data,
    )

    assert len(tasks) == 4
    assert len(rows) == 4
    assert failures == []
    assert rows[0]["payload"] == "alpha"


def test_pipeline_filters():
    records = [{"id": "A"}, {"id": "B"}]

    prevent_duplicate_ids(records, "id", "unit")
    assert limit_by_task_budget(records, max_tasks=3, tasks_per_item=2) == records[:1]
    assert filter_tasks_by_predicate([1, 2, 3], lambda item: item > 1) == [2, 3]


def test_pipeline_metrics_match_existing_score_shape():
    scored = add_research_score_columns(_sample_report())

    assert "Overall Score" in scored.columns
    assert scored.iloc[0]["PF Score"] == 15.0


def test_report_generation_and_csv_loading():
    with TemporaryDirectory() as directory:
        csv_path = str(Path(directory) / "report.csv")
        json_path = str(Path(directory) / "report.json")
        save_csv_report(_sample_report(), csv_path)
        save_json_report({"ok": True}, json_path)
        loaded = load_csv_report(csv_path, {"Profit Factor"})

    assert loaded.iloc[0]["Profit Factor"] == 1.2


def test_generated_candidate_task_builder_backward_compatibility():
    tasks = _build_tasks([{"name": "alpha"}], ["BTCUSDT"], "15m")

    assert len(tasks) == 1
    assert tasks[0].pair == "BTCUSDT"
    assert tasks[0].payload["name"] == "alpha"


def test_existing_score_wrapper_still_works():
    scored = _score_report(_sample_report())

    assert "Overall Score" in scored.columns


def test_duplicate_strategy_wrapper_still_raises():
    try:
        _prevent_duplicate_strategy_ids([
            {"strategy_id": "DUP"},
            {"strategy_id": "DUP"},
        ])
    except ValueError as error:
        assert "Duplicate strategy ID" in str(error)
    else:
        raise AssertionError("Duplicate strategy IDs did not fail")


def test_existing_config_loaders_still_work():
    strategy_config = load_strategy_template_config()
    experiment_config = load_experiment_config()

    assert "include_fixed_strategies" in strategy_config
    assert experiment_config["enabled"] is False


def test_disabled_research_commands_stay_lightweight():
    experiment_report, experiment_summary = run_generated_candidate_experiment({
        "enabled": False,
    })
    robustness_report, shortlist = run_generated_strategy_robustness({
        "enabled": False,
    })

    assert experiment_report.empty
    assert experiment_summary == {}
    assert robustness_report.empty
    assert shortlist == []


if __name__ == "__main__":
    test_pipeline_context_creation()
    test_json_config_loading_with_defaults_and_required_keys()
    test_market_data_loader_uses_injected_loader()
    test_task_generation_and_sequential_execution()
    test_pipeline_filters()
    test_pipeline_metrics_match_existing_score_shape()
    test_report_generation_and_csv_loading()
    test_generated_candidate_task_builder_backward_compatibility()
    test_existing_score_wrapper_still_works()
    test_duplicate_strategy_wrapper_still_raises()
    test_existing_config_loaders_still_work()
    test_disabled_research_commands_stay_lightweight()
    print("test_research_pipeline passed")
