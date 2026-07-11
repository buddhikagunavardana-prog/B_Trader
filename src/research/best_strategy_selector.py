import os
import pandas as pd

from src.research.strategy_scoring_engine import StrategyScoringEngine


REPORT_PATH = "reports/strategy_combination_report.csv"
TOP_5_PATH = "reports/top_5_strategies.csv"
WALK_FORWARD_REPORT_PATH = "reports/walk_forward_report.csv"


def _load_walk_forward_scores() -> pd.DataFrame:
    if not os.path.exists(WALK_FORWARD_REPORT_PATH):
        return pd.DataFrame(columns=["Strategy", "Pair", "Walk Forward Score"])

    walk_forward = pd.read_csv(WALK_FORWARD_REPORT_PATH)

    if walk_forward.empty:
        return pd.DataFrame(columns=["Strategy", "Pair", "Walk Forward Score"])

    return (
        walk_forward
        .groupby(["Strategy", "Pair"], as_index=False)["Walk Forward Score"]
        .mean()
    )


def select_top_5_strategies():
    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(
            "strategy_combination_report.csv not found. "
            "Run: python -m src.research.strategy_combination_lab"
        )

    report = pd.read_csv(REPORT_PATH)

    scoring_engine = StrategyScoringEngine()
    scored_report = scoring_engine.score_report(report)
    scored_report = scored_report.rename(
        columns={"Final Score": "Advanced Score"}
    )

    walk_forward_scores = _load_walk_forward_scores()
    scored_report = scored_report.merge(
        walk_forward_scores,
        on=["Strategy", "Pair"],
        how="left",
    )
    scored_report["Walk Forward Score"] = (
        scored_report["Walk Forward Score"].fillna(0)
    )
    scored_report["Overall Score"] = (
        scored_report["Advanced Score"] * 0.50
        + scored_report["Walk Forward Score"] * 0.50
    ).round(2)

    top_5 = scored_report.sort_values(
        by=["Overall Score", "Advanced Score", "Profit Factor", "ROI %"],
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
            "Advanced Score",
            "Walk Forward Score",
            "Overall Score",
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
