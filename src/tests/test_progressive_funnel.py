import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.research.progressive_funnel import (
    evaluate_funnel_stage, funnel_config_hash, load_funnel_config,
)
from src.research.orchestrator.orchestrator_registry import (
    PRODUCTION, build_default_stage_registry,
)
from src.research.orchestrator.orchestrator_state import (
    OrchestratorState, validate_completed_stage_artifacts,
)


def _trades(strategy="A", pnl=1.0):
    dates = pd.date_range("2025-01-01", "2025-12-31", periods=48, tz="UTC")
    return pd.DataFrame({"Strategy ID": strategy, "Pair": "BTCUSDT", "Entry Time": dates, "PnL %": pnl})


def test_stage_contracts_and_progressive_filtering():
    config = load_funnel_config()
    assert [stage["history_months"] for stage in config["stages"]] == [3, 6, 12]
    assert funnel_config_hash(config) == funnel_config_hash(load_funnel_config())
    candidates = pd.DataFrame([
        {"Strategy ID": "A", "Pair": "BTCUSDT", "Overall Score": 75.0},
        {"Strategy ID": "B", "Pair": "BTCUSDT", "Overall Score": 74.0},
    ])
    trades = pd.concat([_trades("A", 1.0), _trades("B", -1.0)], ignore_index=True)
    result = evaluate_funnel_stage(candidates, trades, config["stages"][0], config)
    assert result.set_index("Strategy ID").loc["A", "Funnel Status"] == "PASS"
    assert result.set_index("Strategy ID").loc["B", "Funnel Status"] == "REJECT"
    assert result.set_index("Strategy ID").loc["A", "Overall Score"] == 75.0


def test_empty_trades_reject_and_validation():
    config = load_funnel_config()
    candidates = pd.DataFrame([{"Strategy ID": "A", "Pair": "BTCUSDT"}])
    empty = pd.DataFrame(columns=["Strategy ID", "Pair", "Entry Time", "PnL %"])
    result = evaluate_funnel_stage(candidates, empty, config["stages"][0], config)
    assert result.iloc[0]["Funnel Status"] == "REJECT"
    with TemporaryDirectory() as directory:
        path = Path(directory, "bad.json")
        bad = dict(config)
        bad["stages"] = [dict(config["stages"][0], history_months=4)]
        path.write_text(json.dumps(bad), encoding="utf-8")
        try:
            load_funnel_config(path)
            raise AssertionError("invalid partition total accepted")
        except ValueError as error:
            assert "Partition months" in str(error)


def test_numeric_trade_indices_are_rejected_as_timestamps():
    config = load_funnel_config()
    candidates = pd.DataFrame([{"Strategy ID": "A", "Pair": "BTCUSDT"}])
    trades = pd.DataFrame({
        "Strategy ID": ["A"],
        "Pair": ["BTCUSDT"],
        "Entry Time": [42],
        "PnL %": [1.0],
    })

    try:
        evaluate_funnel_stage(candidates, trades, config["stages"][0], config)
    except ValueError as error:
        assert "calendar timestamps" in str(error)
    else:
        raise AssertionError("Numeric trade row index was accepted as a timestamp")


def test_production_registry_contract():
    registry = build_default_stage_registry(PRODUCTION)
    assert registry["funnel_3m"].dependencies == ["generated_candidate_research"]
    assert registry["funnel_6m"].dependencies == ["funnel_3m"]
    assert registry["funnel_1y"].dependencies == ["funnel_6m"]
    assert registry["optimization_search"].dependencies == ["funnel_1y"]
    assert registry["funnel_1y"].metadata["output_artifact"] == "funnel_final_survivors"


def test_resume_rejects_stale_funnel_config():
    state = OrchestratorState(
        run_id="unit", config_hash="global", created_at="now", updated_at="now",
        artifact_manifest=[{
            "path": __file__, "producer_stage": "funnel_3m", "required": True,
            "metadata": {"contract_version": "1", "funnel_config_hash": "old"},
        }],
    )
    assert validate_completed_stage_artifacts(state, "funnel_3m", "1")
    assert not validate_completed_stage_artifacts(
        state, "funnel_3m", "1", {"funnel_config_hash": "new"},
    )


if __name__ == "__main__":
    test_stage_contracts_and_progressive_filtering()
    test_empty_trades_reject_and_validation()
    test_numeric_trade_indices_are_rejected_as_timestamps()
    test_production_registry_contract()
    test_resume_rejects_stale_funnel_config()
    print("test_progressive_funnel passed")
