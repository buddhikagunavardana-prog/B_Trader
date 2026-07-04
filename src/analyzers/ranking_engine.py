import pandas as pd


class RankingEngine:

    @staticmethod
    def calculate_score(df):

        ranked_df = df.copy()

        # Normalize values (0-100)

        ranked_df["PF Score"] = (
            ranked_df["Profit Factor"] /
            ranked_df["Profit Factor"].max()
        ) * 100

        ranked_df["PnL Score"] = (
            ranked_df["Total PnL %"] /
            ranked_df["Total PnL %"].max()
        ) * 100

        ranked_df["Win Score"] = (
            ranked_df["Win Rate %"] /
            ranked_df["Win Rate %"].max()
        ) * 100

        ranked_df["Trade Score"] = (
            ranked_df["Trades"] /
            ranked_df["Trades"].max()
        ) * 100

        # Final weighted score

        ranked_df["Overall Score"] = (

            ranked_df["PF Score"] * 0.40 +

            ranked_df["PnL Score"] * 0.30 +

            ranked_df["Win Score"] * 0.20 +

            ranked_df["Trade Score"] * 0.10

        )

        ranked_df = ranked_df.sort_values(
            by="Overall Score",
            ascending=False
        )

        return ranked_df