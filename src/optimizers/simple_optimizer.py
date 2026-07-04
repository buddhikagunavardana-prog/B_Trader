import copy
import pandas as pd


class SimpleOptimizer:
    def __init__(self, strategy_config, indicator_engine, signal_engine, backtest_engine_class):
        self.base_strategy_config = strategy_config
        self.indicator_engine = indicator_engine
        self.signal_engine = signal_engine
        self.backtest_engine_class = backtest_engine_class

    def run(self, df, sl_values, tp_values):
        results = []

        for sl in sl_values:
            for tp in tp_values:
                strategy_config = copy.deepcopy(self.base_strategy_config)

                strategy_config["risk"]["stop_loss_percent"] = sl
                strategy_config["risk"]["take_profit_percent"] = tp

                df_with_indicators = self.indicator_engine.run(df.copy(), strategy_config)
                signals = self.signal_engine.run(df_with_indicators, strategy_config)

                backtest_engine = self.backtest_engine_class(strategy_config)
                result = backtest_engine.run(df_with_indicators, signals)

                results.append({
                    "SL %": sl,
                    "TP %": tp,
                    "Total Trades": result["total_trades"],
                    "Wins": result["wins"],
                    "Losses": result["losses"],
                    "Win Rate %": result["win_rate"],
                    "Total PnL %": result["total_pnl"],
                    "Profit Factor": result["profit_factor"],
                })

        results_df = pd.DataFrame(results)

        results_df = results_df.sort_values(
            by=["Profit Factor", "Total PnL %"],
            ascending=False
        )

        return results_df