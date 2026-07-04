import copy
import pandas as pd

from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.engines.backtest_engine import BacktestEngine


class OptimizerEngine:
    def __init__(self, strategy):
        self.strategy = strategy

    def optimize(self, df, sl_values, tp_values):
        results = []

        for sl in sl_values:
            for tp in tp_values:
                test_strategy = copy.deepcopy(self.strategy)

                test_strategy.exit_rules["stop_loss_percent"] = sl
                test_strategy.exit_rules["take_profit_percent"] = tp

                test_df = df.copy()

                test_df = calculate_indicators(test_df, test_strategy)
                test_df = generate_signals(test_df, test_strategy)

                backtest = BacktestEngine(test_strategy)
                result = backtest.run(test_df, test_df["SIGNAL"])

                results.append({
                    "SL %": sl,
                    "TP %": tp,
                    "Total Trades": result["total_trades"],
                    "Wins": result["wins"],
                    "Losses": result["losses"],
                    "Win Rate %": result["win_rate"],
                    "Total PnL %": result["total_pnl_percent"],
                    "Profit Factor": result["profit_factor"],
                })

        results_df = pd.DataFrame(results)

        results_df = results_df.sort_values(
            by=["Profit Factor", "Total PnL %"],
            ascending=False
        )

        return results_df