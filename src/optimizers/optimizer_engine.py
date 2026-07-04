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

                backtest = BacktestEngine(
                    strategy=test_strategy,
                    initial_balance=10000,
                    stop_loss_pct=sl,
                    take_profit_pct=tp,
                    fee_pct=0.0
                )

                result = backtest.run(test_df, test_df["SIGNAL"])
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

        results_df = results_df.sort_values(
            by=["Profit Factor", "ROI %"],
            ascending=False
        )

        return results_df