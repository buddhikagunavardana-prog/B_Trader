import os
import pandas as pd


REPORT_PATH = "reports/strategy_combination_report.csv"
TOP_5_PATH = "reports/top_5_strategies.csv"


def select_top_5_strategies():
    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(
            "strategy_combination_report.csv not found. "
            "Run: python -m src.research.strategy_combination_lab"
        )

    report = pd.read_csv(REPORT_PATH)

    filtered = report[
        (report["Profit Factor"] >= 1.0)
        & (report["Trades"] >= 20)
        & (report["Max Drawdown %"].abs() <= 35)
    ]

    if filtered.empty:
        filtered = report.copy()

    top_5 = filtered.sort_values(
        by=["Overall Score", "Profit Factor", "Win Rate %"],
        ascending=False
    ).head(5)

    os.makedirs("reports", exist_ok=True)
    top_5.to_csv(TOP_5_PATH, index=False)

    print("\n===== TOP 5 STRATEGIES =====")
    print(top_5.to_string(index=False))
    print(f"\nSaved -> {TOP_5_PATH}")

    return top_5


if __name__ == "__main__":
    select_top_5_strategies()