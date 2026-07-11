import copy
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.engines.backtest_engine import BacktestEngine
from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.research.market_regime_engine import (
    REGIME_STRATEGY_FAMILIES,
    detect_market_regime,
    load_market_regime_config,
)
from src.strategies.strategy_factory import (
    get_generated_strategy_combinations,
    get_strategy_combinations,
)


REPORT_PATH = "reports/strategy_combination_report.csv"
STRATEGY_TEMPLATE_CONFIG_PATH = Path("src/config/strategy_templates.json")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
TIMEFRAME = "15m"
LOOKBACK = "1 year ago UTC"
PREVIOUS_RUNTIME_MINUTES = 34.0
MAX_WORKERS = min(4, os.cpu_count() or 1)

_WORKER_MARKET_DATA = {}


def load_strategy_template_config(
    config_path: Path = STRATEGY_TEMPLATE_CONFIG_PATH,
) -> dict:
    if not config_path.exists():
        return {
            "use_generated_candidates": False,
            "include_fixed_strategies": True,
            "global_max_candidates": 60,
            "enabled_templates": [],
        }

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_research_strategies(config: dict):
    fixed_strategies = []
    generated_strategies = []

    if config.get("include_fixed_strategies", True):
        fixed_strategies = get_strategy_combinations()

    if config.get("use_generated_candidates", False):
        generated_strategies = get_generated_strategy_combinations(
            enabled_templates=config.get("enabled_templates", []),
            global_max_candidates=config.get("global_max_candidates", 60),
        )

    print(f"Active fixed strategies: {len(fixed_strategies)}")
    print(f"Generated candidates: {len(generated_strategies)}")
    print(f"Total research candidates: {len(fixed_strategies) + len(generated_strategies)}")

    return fixed_strategies + generated_strategies


def _strategy_matches_regime(strategy_name: str, regime: str) -> bool:
    strategy_name_lower = strategy_name.lower()
    families = REGIME_STRATEGY_FAMILIES.get(regime, [])

    for family in families:
        family_lower = family.lower()
        if family_lower in strategy_name_lower:
            return True

        if "ema" in family_lower and "ema" in strategy_name_lower:
            return True

        if "supertrend" in family_lower and "supertrend" in strategy_name_lower:
            return True

        if "bollinger" in family_lower and "bollinger" in strategy_name_lower:
            return True

        if "rsi" in family_lower and "rsi" in strategy_name_lower:
            return True

        if "atr" in family_lower and "atr" in strategy_name_lower:
            return True

    return False


def _build_regime_map(market_data: dict, config: dict) -> dict:
    if (
        not config.get("enabled", True)
        or not config.get("regime_filtering_enabled", False)
    ):
        return {}

    return {
        symbol: detect_market_regime(df, config)
        for symbol, df in market_data.items()
    }


def _filter_tasks_by_regime(tasks: list, regime_map: dict, config: dict) -> list:
    if not config.get("regime_filtering_enabled", False):
        return tasks

    filtered_tasks = []

    for task in tasks:
        _, _, symbol, strategy, _, _ = task
        regime = regime_map.get(symbol, {}).get("regime")

        if regime and _strategy_matches_regime(strategy.name, regime):
            filtered_tasks.append(task)

    return filtered_tasks or tasks


def _initialize_worker(market_data):
    global _WORKER_MARKET_DATA
    _WORKER_MARKET_DATA = market_data


def _run_backtest_grid(df, strategy, sl_values, tp_values):
    results = []
    signal_strategy = copy.deepcopy(strategy)
    signal_df = calculate_indicators(df.copy(), signal_strategy)
    signal_df = generate_signals(signal_df, signal_strategy)
    signals = signal_df["SIGNAL"]

    for sl in sl_values:
        for tp in tp_values:
            test_strategy = copy.deepcopy(strategy)
            test_strategy.exit_rules["stop_loss_percent"] = sl
            test_strategy.exit_rules["take_profit_percent"] = tp

            backtest = BacktestEngine(
                strategy=test_strategy,
                initial_balance=10000,
                stop_loss_pct=sl,
                take_profit_pct=tp,
                fee_pct=0.0,
            )

            result = backtest.run(signal_df, signals)
            result_dict = result.to_dict()

            results.append({
                "SL %": sl,
                "TP %": tp,
                "Initial Balance": result_dict["initial_balance"],
                "Final Balance": result_dict["final_balance"],
                "Gross Profit": result_dict["gross_profit"],
                "Gross Loss": result_dict["gross_loss"],
                "Net Profit": result_dict["net_profit"],
                "ROI %": result_dict["roi_pct"],
                "Max Drawdown %": result_dict["max_drawdown_pct"],
                "Fees Paid": result_dict["total_fees"],
                "Total Trades": result_dict["total_trades"],
                "Wins": result_dict["wins"],
                "Losses": result_dict["losses"],
                "Win Rate %": result_dict["win_rate"],
                "Total PnL %": result_dict["total_pnl_pct"],
                "Profit Factor": result_dict["profit_factor"],
                "Avg Win": result_dict["avg_win"],
                "Avg Loss": result_dict["avg_loss"],
                "Largest Win": result_dict["largest_win"],
                "Largest Loss": result_dict["largest_loss"],
                "Expectancy": result_dict["expectancy"],
            })

    results_df = pd.DataFrame(results)

    return results_df.sort_values(
        by=["Profit Factor", "ROI %"],
        ascending=False,
    )


def _evaluate_strategy_pair(task):
    strategy_index, pair_index, symbol, strategy, sl_values, tp_values = task
    df = _WORKER_MARKET_DATA[symbol].copy()
    results = _run_backtest_grid(df, strategy, sl_values, tp_values)
    best = results.iloc[0]

    return {
        "strategy_index": strategy_index,
        "pair_index": pair_index,
        "Strategy": strategy.name,
        "Pair": symbol,
        "Timeframe": TIMEFRAME,
        "SL %": best["SL %"],
        "TP %": best["TP %"],
        "Initial Balance": best["Initial Balance"],
        "Final Balance": best["Final Balance"],
        "Net Profit": best["Net Profit"],
        "ROI %": best["ROI %"],
        "Max Drawdown %": best["Max Drawdown %"],
        "Profit Factor": best["Profit Factor"],
        "Total PnL %": best["Total PnL %"],
        "Win Rate %": best["Win Rate %"],
        "Trades": best["Total Trades"],
        "Expectancy": best["Expectancy"],
    }


def run_strategy_combination_lab():
    started_at = time.perf_counter()
    sl_values = [1, 1.5, 2, 2.5]
    tp_values = [2, 3, 4, 5]

    template_config = load_strategy_template_config()
    combinations = _load_research_strategies(template_config)
    final_results = []
    market_data = {}
    regime_config = load_market_regime_config()

    print("\n===== B TRADER 15m STRATEGY COMBINATION LAB =====")
    print(f"Previous runtime baseline: ~{PREVIOUS_RUNTIME_MINUTES:.1f} minutes")
    print(f"Parallel workers: {MAX_WORKERS}")

    for symbol in SYMBOLS:
        print(f"Loading cached data: {symbol} | Timeframe: {TIMEFRAME}")
        market_data[symbol] = get_cached_klines(
            symbol=symbol,
            timeframe=TIMEFRAME,
            lookback=LOOKBACK,
        )

    tasks = [
        (strategy_index, pair_index, symbol, strategy, sl_values, tp_values)
        for strategy_index, strategy in enumerate(combinations)
        for pair_index, symbol in enumerate(SYMBOLS)
    ]
    regime_map = _build_regime_map(market_data, regime_config)
    tasks = _filter_tasks_by_regime(tasks, regime_map, regime_config)

    if regime_config.get("regime_filtering_enabled", False):
        print(f"Regime filtering enabled: {len(tasks)} tasks selected")
    else:
        print("Regime filtering disabled: running all strategy/pair tasks")

    total_tasks = len(tasks)
    completed_tasks = 0
    failures = []

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=_initialize_worker,
        initargs=(market_data,),
    ) as executor:
        future_map = {
            executor.submit(_evaluate_strategy_pair, task): task
            for task in tasks
        }

        for future in as_completed(future_map):
            strategy_index, _, symbol, strategy, _, _ = future_map[future]
            completed_tasks += 1
            progress_pct = completed_tasks / total_tasks * 100

            try:
                final_results.append(future.result())
                print(
                    f"[{progress_pct:6.2f}%] Done: "
                    f"{strategy.name} | {symbol}"
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

    if not final_results:
        raise RuntimeError("No strategy research results were generated")

    if failures:
        print("\nResearch completed with failures:")
        for failure in failures:
            print(
                f"  {failure['strategy']} | {failure['symbol']} | "
                f"{failure['error']}"
            )

    report = pd.DataFrame(final_results)

    report["PF Score"] = report["Profit Factor"].clip(0, 2) / 2 * 25
    report["PnL Score"] = report["Total PnL %"].clip(0, 50) / 50 * 25
    report["Win Score"] = report["Win Rate %"].clip(0, 60) / 60 * 20
    report["DD Score"] = (
        1 - report["Max Drawdown %"].abs().clip(0, 40) / 40
    ) * 20
    report["Trade Score"] = report["Trades"].clip(0, 200) / 200 * 10

    report["Overall Score"] = (
        report["PF Score"]
        + report["PnL Score"]
        + report["Win Score"]
        + report["DD Score"]
        + report["Trade Score"]
    )

    report = report.sort_values(
        by=[
            "Overall Score",
            "Profit Factor",
            "ROI %",
            "strategy_index",
            "pair_index",
        ],
        ascending=[False, False, False, True, True],
    )
    report = report.drop(columns=["strategy_index", "pair_index"])

    os.makedirs("reports", exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)

    elapsed_minutes = (time.perf_counter() - started_at) / 60

    print("\nReport saved -> reports/strategy_combination_report.csv")
    print(f"Previous runtime: ~{PREVIOUS_RUNTIME_MINUTES:.1f} minutes")
    print(f"New runtime: {elapsed_minutes:.2f} minutes")
    print("Biggest impact: one indicator/signal pass per strategy/pair")
    print(report.head(20).to_string(index=False))

    return report


if __name__ == "__main__":
    run_strategy_combination_lab()
