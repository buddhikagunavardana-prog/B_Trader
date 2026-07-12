from types import SimpleNamespace
import sys
import time

import pandas as pd

from src.engines.backtest_engine import BacktestEngine


def _strategy():
    return SimpleNamespace(exit_rules={})


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
    if "--benchmark" in sys.argv:
        run_cached_worker_benchmark()
    print("test_backtest_performance passed")
