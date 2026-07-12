import copy
import os
import time
from pathlib import Path

import pandas as pd

from src.engines.backtest_engine import BacktestEngine
from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.research.market_regime_engine import (
    REGIME_STRATEGY_FAMILIES,
    detect_market_regime,
    load_market_regime_config,
)
from src.research.pipeline.pipeline_executor import (
    execute_tasks,
    get_worker_market_data,
)
from src.research.pipeline.pipeline_loader import load_json_config, load_market_data
from src.research.pipeline.pipeline_metrics import add_research_score_columns
from src.research.pipeline.pipeline_reporter import save_csv_report
from src.research.pipeline.pipeline_runner import build_strategy_pair_tasks
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


def load_strategy_template_config(
    config_path: Path = STRATEGY_TEMPLATE_CONFIG_PATH,
) -> dict:
    return load_json_config(
        config_path,
        defaults={
            "use_generated_candidates": False,
            "include_fixed_strategies": True,
            "global_max_candidates": 60,
            "enabled_templates": [],
        },
    )


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
        symbol = task.pair
        strategy = task.payload
        regime = regime_map.get(symbol, {}).get("regime")

        if regime and _strategy_matches_regime(strategy.name, regime):
            filtered_tasks.append(task)

    return filtered_tasks or tasks


def _run_backtest_grid(
    df,
    strategy,
    sl_values,
    tp_values,
    include_trade_details=False,
):
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

            row = {
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
            }
            if include_trade_details:
                row["_Trade Records"] = result_dict["trades"]
            results.append(row)

    results_df = pd.DataFrame(results)

    return results_df.sort_values(
        by=["Profit Factor", "ROI %"],
        ascending=False,
    )


def _evaluate_strategy_pair(task):
    strategy_index = task.item_index
    pair_index = task.pair_index
    symbol = task.pair
    strategy = task.payload
    sl_values = task.metadata["sl_values"]
    tp_values = task.metadata["tp_values"]
    df = get_worker_market_data(symbol).copy()
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
    regime_config = load_market_regime_config()

    print("\n===== B TRADER 15m STRATEGY COMBINATION LAB =====")
    print(f"Previous runtime baseline: ~{PREVIOUS_RUNTIME_MINUTES:.1f} minutes")
    print(f"Parallel workers: {MAX_WORKERS}")

    market_data = load_market_data(
        SYMBOLS,
        TIMEFRAME,
        LOOKBACK,
        logger=print,
    )
    tasks = build_strategy_pair_tasks(
        combinations,
        SYMBOLS,
        TIMEFRAME,
        metadata_builder=lambda _strategy, _pair: {
            "sl_values": sl_values,
            "tp_values": tp_values,
        },
    )
    regime_map = _build_regime_map(market_data, regime_config)
    tasks = _filter_tasks_by_regime(tasks, regime_map, regime_config)

    if regime_config.get("regime_filtering_enabled", False):
        print(f"Regime filtering enabled: {len(tasks)} tasks selected")
    else:
        print("Regime filtering disabled: running all strategy/pair tasks")

    total_tasks = len(tasks)

    def _progress(completed_tasks, task_count, task, error):
        progress_pct = completed_tasks / task_count * 100
        strategy = task.payload
        if error:
            print(
                f"[{progress_pct:6.2f}%] Failed: "
                f"{strategy.name} | {task.pair} | {error}"
            )
            return

        print(f"[{progress_pct:6.2f}%] Done: {strategy.name} | {task.pair}")

    final_results, failures = execute_tasks(
        tasks,
        _evaluate_strategy_pair,
        MAX_WORKERS,
        market_data=market_data,
        progress_callback=_progress,
    )

    if not final_results:
        raise RuntimeError("No strategy research results were generated")

    if failures:
        print("\nResearch completed with failures:")
        for failure in failures:
            task = failure["task"]
            print(
                f"  {task.payload.name} | {task.pair} | "
                f"{failure['error']}"
            )

    report = pd.DataFrame(final_results)

    report = add_research_score_columns(report)
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

    save_csv_report(report, REPORT_PATH)

    elapsed_minutes = (time.perf_counter() - started_at) / 60

    print("\nReport saved -> reports/strategy_combination_report.csv")
    print(f"Previous runtime: ~{PREVIOUS_RUNTIME_MINUTES:.1f} minutes")
    print(f"New runtime: {elapsed_minutes:.2f} minutes")
    print("Biggest impact: one indicator/signal pass per strategy/pair")
    print(report.head(20).to_string(index=False))

    return report


if __name__ == "__main__":
    run_strategy_combination_lab()
