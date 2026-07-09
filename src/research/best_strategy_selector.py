import os
import pandas as pd

from src.research.strategy_scoring_engine import StrategyScoringEngine


REPORT_PATH = "reports/strategy_combination_report.csv"
TOP_5_PATH = "reports/top_5_strategies.csv"


def select_top_5_strategies():
    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(
            "strategy_combination_report.csv not found. "
            "Run: python -m src.research.strategy_combination_lab"
        )

    report = pd.read_csv(REPORT_PATH)

    scoring_engine = StrategyScoringEngine()
    scored_report = scoring_engine.score_report(report)

    top_5 = scored_report.sort_values(
        by=["Final Score", "Profit Factor", "ROI %"],
        ascending=False
    ).head(5)

    top_5 = top_5.reset_index(drop=True)
    top_5["Rank"] = top_5.index + 1

    top_5 = top_5[
        [
            "Rank",
            "Strategy",
            "Pair",
            "ROI %",
            "Profit Factor",
            "Win Rate %",
            "Max Drawdown %",
            "Trades",
            "Expectancy",
            "Stability Score",
            "Final Score",
        ]
    ].rename(
        columns={
            "ROI %": "ROI",
            "Win Rate %": "Win Rate",
            "Max Drawdown %": "Max Drawdown",
            "Trades": "Trade Count",
        }
    )

    os.makedirs("reports", exist_ok=True)
    top_5.to_csv(TOP_5_PATH, index=False)

    print("\n===== TOP 5 STRATEGIES =====")
    print(top_5.to_string(index=False))
    print(f"\nSaved -> {TOP_5_PATH}")

    return top_5


if __name__ == "__main__":
    select_top_5_strategies()
