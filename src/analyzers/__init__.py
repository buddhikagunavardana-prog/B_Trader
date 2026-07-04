from src.plugins.binance_data import download_klines
from src.optimizers.optimizer_engine import OptimizerEngine


class MultiPairAnalyzer:

    def __init__(self, strategy):
        self.strategy = strategy
        self.optimizer = OptimizerEngine(strategy)

    def analyze(
        self,
        symbols,
        interval="1h",
        start_str="1 year ago UTC",
        sl_values=[1, 1.5, 2, 2.5],
        tp_values=[2, 3, 4, 5]
    ):

        final_results = []

        for symbol in symbols:

            print(f"\nTesting {symbol}...")

            df = download_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str
            )

            results = self.optimizer.optimize(
                df=df,
                sl_values=sl_values,
                tp_values=tp_values
            )

            best = results.iloc[0]

            final_results.append({

                "Pair": symbol,

                "SL %": best["SL %"],
                "TP %": best["TP %"],

                "Profit Factor": best["Profit Factor"],

                "Total PnL %": best["Total PnL %"],

                "Win Rate %": best["Win Rate %"],

                "Trades": best["Total Trades"]

            })

        return final_results