import copy
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.research.strategy_combination_lab import (
    LOOKBACK,
    MAX_WORKERS,
    SYMBOLS,
    TIMEFRAME,
    _run_backtest_grid,
)
from src.strategies.strategy_factory import get_strategy_combinations


CONFIG_PATH = Path("src/config/walk_forward.json")
REPORT_PATH = "reports/walk_forward_report.csv"

_WORKER_MARKET_DATA = {}


def load_walk_forward_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    required_keys = [
        "train_days",
        "test_days",
        "step_days",
        "minimum_trades",
        "pass_score",
    ]

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing walk-forward config key: {key}")

    return config


def _initialize_worker(market_data):
    global _WORKER_MARKET_DATA
    _WORKER_MARKET_DATA = market_data


def _prepare_market_data(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    if "open_time" not in prepared.columns:
        raise ValueError("OHLCV data must include open_time")

    prepared["open_time"] = pd.to_datetime(prepared["open_time"])
    prepared = prepared.sort_values("open_time").reset_index(drop=True)

    return prepared


def build_walk_forward_windows(df: pd.DataFrame, config: dict) -> list[dict]:
    prepared = _prepare_market_data(df)

    train_delta = pd.Timedelta(days=config["train_days"])
    test_delta = pd.Timedelta(days=config["test_days"])
    step_delta = pd.Timedelta(days=config["step_days"])

    first_time = prepared["open_time"].min()
    last_time = prepared["open_time"].max()

    windows = []
    train_start = first_time

    while True:
        train_end = train_start + train_delta
        test_start = train_end
        test_end = test_start + test_delta

        if test_end > last_time:
            break

        train_df = prepared[
            (prepared["open_time"] >= train_start)
            & (prepared["open_time"] < train_end)
        ].copy()
        test_df = prepared[
            (prepared["open_time"] >= test_start)
            & (prepared["open_time"] < test_end)
        ].copy()

        if not train_df.empty and not test_df.empty:
            windows.append({
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "train_df": train_df,
                "test_df": test_df,
            })

        train_start = train_start + step_delta

    return windows


def _retention_score(train_value, test_value) -> float:
    train_value = float(train_value)
    test_value = float(test_value)

    if train_value <= 0:
        return 100.0 if test_value > 0 else 0.0

    return max(0.0, min(test_value / train_value, 1.0)) * 100


def _drawdown_stability_score(train_drawdown, test_drawdown) -> float:
    train_abs = abs(float(train_drawdown))
    test_abs = abs(float(test_drawdown))

    if test_abs <= train_abs:
        return 100.0

    return max(0.0, 100.0 - ((test_abs - train_abs) / 40.0 * 100.0))


def _trade_count_score(test_trades, minimum_trades) -> float:
    return max(0.0, min(float(test_trades) / minimum_trades, 1.0)) * 100


def calculate_walk_forward_score(train_best, test_best, config: dict) -> float:
    roi_score = _retention_score(train_best["ROI %"], test_best["ROI %"])
    win_score = _retention_score(
        train_best["Win Rate %"],
        test_best["Win Rate %"],
    )
    pf_score = _retention_score(
        train_best["Profit Factor"],
        test_best["Profit Factor"],
    )
    drawdown_score = _drawdown_stability_score(
        train_best["Max Drawdown %"],
        test_best["Max Drawdown %"],
    )
    trade_score = _trade_count_score(
        test_best["Total Trades"],
        config["minimum_trades"],
    )

    score = (
        roi_score * 0.30
        + win_score * 0.25
        + pf_score * 0.25
        + drawdown_score * 0.10
        + trade_score * 0.10
    )

    return round(score, 2)


def _evaluate_walk_forward_task(task):
    strategy_index, pair_index, symbol, strategy, config = task
    df = _WORKER_MARKET_DATA[symbol]
    windows = build_walk_forward_windows(df, config)
    rows = []

    for window_index, window in enumerate(windows):
        train_results = _run_backtest_grid(
            window["train_df"],
            strategy,
            [1, 1.5, 2, 2.5],
            [2, 3, 4, 5],
        )
        train_best = train_results.iloc[0]

        test_strategy = copy.deepcopy(strategy)
        test_results = _run_backtest_grid(
            window["test_df"],
            test_strategy,
            [train_best["SL %"]],
            [train_best["TP %"]],
        )
        test_best = test_results.iloc[0]

        walk_forward_score = calculate_walk_forward_score(
            train_best,
            test_best,
            config,
        )
        status = (
            "PASS"
            if (
                walk_forward_score >= config["pass_score"]
                and test_best["Total Trades"] >= config["minimum_trades"]
            )
            else "FAIL"
        )

        rows.append({
            "strategy_index": strategy_index,
            "pair_index": pair_index,
            "window_index": window_index,
            "Strategy": strategy.name,
            "Pair": symbol,
            "Train Start": window["train_start"].date().isoformat(),
            "Train End": window["train_end"].date().isoformat(),
            "Test Start": window["test_start"].date().isoformat(),
            "Test End": window["test_end"].date().isoformat(),
            "Train ROI": train_best["ROI %"],
            "Test ROI": test_best["ROI %"],
            "Train Win Rate": train_best["Win Rate %"],
            "Test Win Rate": test_best["Win Rate %"],
            "Train PF": train_best["Profit Factor"],
            "Test PF": test_best["Profit Factor"],
            "Walk Forward Score": walk_forward_score,
            "Status": status,
        })

    return rows


def run_walk_forward_engine():
    config = load_walk_forward_config()
    strategies = get_strategy_combinations()
    market_data = {}

    print("\n===== B TRADER WALK FORWARD ENGINE =====")
    print(
        "Config: "
        f"train={config['train_days']}d | "
        f"test={config['test_days']}d | "
        f"step={config['step_days']}d"
    )

    for symbol in SYMBOLS:
        print(f"Loading cached data: {symbol} | Timeframe: {TIMEFRAME}")
        market_data[symbol] = get_cached_klines(
            symbol=symbol,
            timeframe=TIMEFRAME,
            lookback=LOOKBACK,
        )

    tasks = [
        (strategy_index, pair_index, symbol, strategy, config)
        for strategy_index, strategy in enumerate(strategies)
        for pair_index, symbol in enumerate(SYMBOLS)
    ]

    rows = []
    failures = []
    total_tasks = len(tasks)
    completed_tasks = 0

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=_initialize_worker,
        initargs=(market_data,),
    ) as executor:
        future_map = {
            executor.submit(_evaluate_walk_forward_task, task): task
            for task in tasks
        }

        for future in as_completed(future_map):
            strategy_index, _, symbol, strategy, _ = future_map[future]
            completed_tasks += 1
            progress_pct = completed_tasks / total_tasks * 100

            try:
                task_rows = future.result()
                rows.extend(task_rows)
                print(
                    f"[{progress_pct:6.2f}%] Done: "
                    f"{strategy.name} | {symbol} | cycles={len(task_rows)}"
                )
            except Exception as error:
                failures.append({
                    "strategy_index": strategy_index,
                    "strategy": strategy.name,
                    "symbol": symbol,
                    "error": str(error),
                })
                print(
                    f"[{progress_pct:6.2f}%] Failed: "
                    f"{strategy.name} | {symbol} | {error}"
                )

    if not rows:
        raise RuntimeError("No walk-forward rows were generated")

    if failures:
        print("\nWalk-forward completed with failures:")
        for failure in failures:
            print(
                f"  {failure['strategy']} | {failure['symbol']} | "
                f"{failure['error']}"
            )

    report = pd.DataFrame(rows)
    report = report.sort_values(
        by=["strategy_index", "pair_index", "window_index"],
        ascending=True,
    )
    report = report.drop(
        columns=["strategy_index", "pair_index", "window_index"],
    )

    os.makedirs("reports", exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)

    print(f"\nReport saved -> {REPORT_PATH}")
    print(report.head(20).to_string(index=False))

    return report


if __name__ == "__main__":
    run_walk_forward_engine()
