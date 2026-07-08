import os
import pandas as pd

from src.plugins.binance_data import download_klines
from src.optimizers.optimizer_engine import OptimizerEngine
from src.research.strategy_factory import get_strategy_combinations
from src.strategies.strategy_loader import load_strategy_config


REPORT_PATH = "reports/strategy_combination_report.csv"


def run_strategy_combination_lab():
    config = load_strategy_config()

    symbols = ["BTCUSDT"]
    timeframe = config["timeframe"]

    sl_values = [1]
    tp_values = [2]

    combinations = get_strategy_combinations()
    final_results = []

    print("\n===== B TRADER 15m STRATEGY COMBINATION LAB =====")

    for strategy in combinations:
        strategy_name = strategy.name

        print(f"\nTesting Strategy: {strategy_name}")

        optimizer = OptimizerEngine(strategy)

        for symbol in symbols:
            print(f"  Pair: {symbol} | Timeframe: {timeframe}")

            df = download_klines(
                symbol=symbol,
                interval=timeframe,
                start_str="1 year ago UTC"
            )

            results = optimizer.optimize(
                df=df,
                sl_values=sl_values,
                tp_values=tp_values
            )

            best = results.iloc[0]

            final_results.append({
                "Strategy": strategy_name,
                "Pair": symbol,
                "Timeframe": timeframe,
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
            })

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
        by=["Overall Score", "Profit Factor", "ROI %"],
        ascending=False
    )

    os.makedirs("reports", exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)

    print("\nReport saved -> reports/strategy_combination_report.csv")
    print(report.head(20).to_string(index=False))

    return report


if __name__ == "__main__":
    run_strategy_combination_lab()