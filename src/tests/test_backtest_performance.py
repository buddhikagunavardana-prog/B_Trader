from types import SimpleNamespace
import sys
import time

import pandas as pd

from src.engines.backtest_engine import BacktestEngine
from src.research.monte_carlo.monte_carlo_input import MonteCarloInput


def _strategy():
    return SimpleNamespace(exit_rules={})


def _atr_strategy(minimum=None, maximum=None):
    rules = {
        "simulated_exit_mode": "atr_full_position",
        "atr_period": 14,
        "atr_stop_multiplier": 1.5,
        "atr_target_multiplier": 3.0,
    }
    if minimum is not None:
        rules["min_stop_percent"] = minimum
    if maximum is not None:
        rules["max_stop_percent"] = maximum
    return SimpleNamespace(exit_rules=rules)


def _risk_strategy(stop_loss=5.0, take_profit=5.0, risk=0.01, cap=0.25):
    return SimpleNamespace(
        exit_rules={
            "stop_loss_percent": stop_loss,
            "take_profit_percent": take_profit,
        },
        risk={
            "position_sizing_mode": "risk_normalized",
            "risk_per_trade_fraction": risk,
            "max_capital_allocation_fraction": cap,
            "leverage_allowed": False,
        },
    )


def test_array_access_preserves_trade_semantics_and_inputs():
    index = pd.date_range("2026-01-01", periods=5, freq="15min")
    market = pd.DataFrame(
        {
            "close": [100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [100.0, 101.0, 103.0, 100.0, 100.0],
            "low": [100.0, 99.0, 99.0, 97.0, 100.0],
        },
        index=index,
    )
    signals = pd.Series(["BUY", "HOLD", "HOLD", "BUY", "HOLD"], index=index)
    original_market = market.copy(deep=True)
    original_signals = signals.copy(deep=True)

    result = BacktestEngine(
        _strategy(),
        initial_balance=10000,
        stop_loss_pct=2,
        take_profit_pct=2,
        fee_pct=0,
    ).run(market, signals)
    payload = result.to_dict()

    pd.testing.assert_frame_equal(market, original_market, check_exact=True)
    pd.testing.assert_series_equal(signals, original_signals, check_exact=True)
    assert payload["total_trades"] == 1
    assert payload["final_balance"] == 10200.0
    assert payload["roi_pct"] == 2.0
    assert payload["trades"] == [
        {
            "trade_id": 1,
            "direction": "LONG",
            "result": "WIN",
            "exit_reason": "TAKE_PROFIT",
            "entry_index": 0,
            "exit_index": 2,
            "duration_candles": 2,
            "entry_time": index[0],
            "exit_time": index[2],
            "entry_price": 100.0,
            "exit_price": 102.0,
            "stop_loss": 98.0,
            "take_profit": 102.0,
            "position_size_percent": 100.0,
            "trade_capital": 10000.0,
            "gross_pnl_pct": 2.0,
            "pnl_pct": 2.0,
            "gross_pnl_amount": 200.0,
            "pnl_amount": 200.0,
            "buy_fee": 0.0,
            "sell_fee": 0.0,
            "total_fee": 0.0,
            "balance_before": 10000.0,
            "balance_after": 10200.0,
        }
    ]


def test_atr_exit_uses_previous_completed_candle_without_lookahead():
    market = pd.DataFrame({
        "close": [100.0, 100.0, 100.0],
        "high": [100.0, 100.0, 107.0],
        "low": [100.0, 100.0, 98.0],
        "ATR14": [2.0, 999.0, 999.0],
    })
    signals = pd.Series(["HOLD", "BUY", "HOLD"])

    result = BacktestEngine(_atr_strategy()).run(market, signals).to_dict()
    trade = result["trades"][0]

    assert trade["entry_index"] == 1
    assert trade["atr_value"] == 2.0
    assert trade["stop_loss"] == 97.0
    assert trade["take_profit"] == 106.0
    assert trade["exit_price"] == 106.0


def test_atr_stop_distance_clamps_and_invalid_values():
    minimum_market = pd.DataFrame({
        "close": [100.0, 100.0, 100.0],
        "high": [100.0, 100.0, 104.0],
        "low": [100.0, 100.0, 98.0],
        "ATR14": [0.1, 0.1, 0.1],
    })
    signals = pd.Series(["HOLD", "BUY", "HOLD"])
    minimum_trade = BacktestEngine(
        _atr_strategy(minimum=1.0, maximum=3.0)
    ).run(minimum_market, signals).to_dict()["trades"][0]
    assert minimum_trade["stop_distance"] == 1.0
    assert minimum_trade["stop_loss"] == 99.0
    assert minimum_trade["take_profit"] == 102.0

    maximum_market = minimum_market.copy()
    maximum_market["ATR14"] = [10.0, 10.0, 10.0]
    maximum_market.loc[2, "low"] = 96.0
    maximum_trade = BacktestEngine(
        _atr_strategy(minimum=1.0, maximum=3.0)
    ).run(maximum_market, signals).to_dict()["trades"][0]
    assert maximum_trade["stop_distance"] == 3.0
    assert maximum_trade["stop_loss"] == 97.0
    assert maximum_trade["take_profit"] == 106.0

    invalid_market = minimum_market.copy()
    invalid_market["ATR14"] = [float("nan"), 1.0, 1.0]
    invalid_signals = pd.Series(["HOLD", "BUY", "BUY"])
    invalid_result = BacktestEngine(_atr_strategy()).run(
        invalid_market,
        invalid_signals,
    ).to_dict()
    assert invalid_result["trades"] == []

    try:
        BacktestEngine(_atr_strategy()).run(
            invalid_market.drop(columns=["ATR14"]),
            invalid_signals,
        )
    except ValueError as error:
        assert "requires market data column ATR14" in str(error)
    else:
        raise AssertionError("Missing ATR column did not fail clearly")


def test_risk_normalized_fixed_stop_quantity_and_metadata():
    market = pd.DataFrame({
        "close": [100.0, 100.0],
        "high": [100.0, 106.0],
        "low": [100.0, 99.0],
    })
    signals = pd.Series(["BUY", "HOLD"])
    result = BacktestEngine(_risk_strategy()).run(market, signals).to_dict()
    trade = result["trades"][0]

    assert trade["risk_budget"] == 100.0
    assert trade["stop_distance"] == 5.0
    assert trade["quantity"] == 20.0
    assert trade["capital_deployed"] == 2000.0
    assert trade["position_size_percent"] == 20.0
    assert trade["actual_stop_risk"] == 100.0
    assert trade["position_sizing_mode"] == "risk_normalized"
    assert trade["pnl_pct"] == 1.0
    assert trade["gross_pnl_pct"] == 5.0

    monte_carlo_input = MonteCarloInput.from_backtest_result(
        strategy_id="RISK_TEST",
        strategy_name="Risk Test",
        pair="BTCUSDT",
        template_type="test",
        result=result,
    )
    assert monte_carlo_input.trade_returns == [1.0]
    assert monte_carlo_input.trade_pnls == [100.0]


def test_risk_normalized_allocation_cash_caps_and_no_leverage():
    market = pd.DataFrame({
        "close": [100.0, 100.0],
        "high": [100.0, 102.0],
        "low": [100.0, 98.0],
    })
    signals = pd.Series(["BUY", "HOLD"])
    capped = BacktestEngine(
        _risk_strategy(stop_loss=1.0, take_profit=1.0)
    ).run(market, signals).to_dict()["trades"][0]
    assert capped["quantity"] == 25.0
    assert capped["capital_deployed"] == 2500.0
    assert capped["actual_stop_risk"] == 25.0

    cash_capped = BacktestEngine(
        _risk_strategy(stop_loss=0.5, take_profit=1.0, risk=1.0, cap=1.0)
    ).run(market, signals).to_dict()["trades"][0]
    assert cash_capped["quantity"] == 100.0
    assert cash_capped["capital_deployed"] == 10000.0

    leveraged = _risk_strategy()
    leveraged.risk["leverage_allowed"] = True
    try:
        BacktestEngine(leveraged).run(market, signals)
    except ValueError as error:
        assert "does not support leverage" in str(error)
    else:
        raise AssertionError("Leveraged Binance Spot sizing was accepted")


def test_risk_normalized_atr_stop_compounding_and_invalid_stop():
    atr_strategy = _atr_strategy()
    atr_strategy.risk = _risk_strategy().risk
    atr_market = pd.DataFrame({
        "close": [100.0, 100.0, 100.0],
        "high": [100.0, 100.0, 107.0],
        "low": [100.0, 100.0, 99.0],
        "ATR14": [2.0, 999.0, 999.0],
    })
    atr_trade = BacktestEngine(atr_strategy).run(
        atr_market,
        pd.Series(["HOLD", "BUY", "HOLD"]),
    ).to_dict()["trades"][0]
    assert atr_trade["stop_distance"] == 3.0
    assert atr_trade["quantity"] == 25.0
    assert atr_trade["capital_deployed"] == 2500.0

    compound_market = pd.DataFrame({
        "close": [100.0, 100.0, 100.0, 100.0],
        "high": [100.0, 106.0, 100.0, 106.0],
        "low": [100.0, 99.0, 100.0, 99.0],
    })
    compound_signals = pd.Series(["BUY", "HOLD", "BUY", "HOLD"])
    first = BacktestEngine(_risk_strategy()).run(
        compound_market,
        compound_signals,
    ).to_dict()
    second = BacktestEngine(_risk_strategy()).run(
        compound_market,
        compound_signals,
    ).to_dict()
    assert first == second
    assert first["final_balance"] == 10201.0
    assert first["trades"][1]["risk_budget"] == 101.0
    assert first["trades"][1]["capital_deployed"] == 2020.0

    invalid = BacktestEngine(
        _risk_strategy(stop_loss=0.0)
    ).run(compound_market, compound_signals).to_dict()
    assert invalid["trades"] == []


def run_cached_worker_benchmark():
    import src.research.generated_candidate_experiment as experiment
    from src.research.pipeline.pipeline_loader import load_market_data

    records = experiment.load_generated_strategy_records(5)
    market_data = load_market_data(["BTCUSDT"], "15m", "1 year ago UTC")
    outcomes = {}
    for workers in (1, 2, 4):
        experiment.MAX_WORKERS = workers
        trades = []
        started = time.perf_counter()
        report, _ = experiment._run_records(
            records, market_data, ["BTCUSDT"], "15m", trades,
        )
        outcomes[workers] = {
            "runtime": time.perf_counter() - started,
            "report": report.drop(columns=["Runtime Seconds"]).reset_index(drop=True),
            "trades": trades,
        }

    baseline = outcomes[1]
    for workers in (2, 4):
        pd.testing.assert_frame_equal(
            baseline["report"], outcomes[workers]["report"], check_exact=True,
        )
        canonical = lambda rows: sorted(
            rows,
            key=lambda row: (
                row["Candidate ID"], row["Pair"], row["Trade ID"],
            ),
        )
        assert canonical(baseline["trades"]) == canonical(outcomes[workers]["trades"])

    print({
        workers: {
            "runtime": round(item["runtime"], 6),
            "speedup_vs_1": round(baseline["runtime"] / item["runtime"], 3),
            "raw_trade_order_equal": item["trades"] == baseline["trades"],
        }
        for workers, item in outcomes.items()
    })


if __name__ == "__main__":
    test_array_access_preserves_trade_semantics_and_inputs()
    test_atr_exit_uses_previous_completed_candle_without_lookahead()
    test_atr_stop_distance_clamps_and_invalid_values()
    test_risk_normalized_fixed_stop_quantity_and_metadata()
    test_risk_normalized_allocation_cash_caps_and_no_leverage()
    test_risk_normalized_atr_stop_compounding_and_invalid_stop()
    if "--benchmark" in sys.argv:
        run_cached_worker_benchmark()
    print("test_backtest_performance passed")
