from pathlib import Path
import pandas as pd


def test_framework_profiling_reports():
    profile = pd.read_csv("reports/framework_profiling_summary.csv")
    assert len(profile) == 280
    assert profile.groupby(["framework", "row_count", "mode"]).size().eq(1).all()
    assert set(profile["measured_runs"]) == {5} and set(profile["warmup_runs"]) == {1}
    assert profile["repeated_indicator_calculations"].eq(0).all()
    assert profile["framework"].nunique() == 35 and profile["mode"].nunique() == 4
    budgets = pd.read_csv("reports/framework_performance_budgets.csv")
    assert len(budgets) == 35 and not budgets["budget_status"].eq("BLOCK").any()
    required = (
        "framework_hotspot_analysis.csv", "framework_performance_before_after.csv",
        "framework_memory_profile.csv", "framework_output_equivalence.csv",
        "framework_optimization_causality.csv", "framework_controller_performance.csv",
    )
    banned = ("pnl", "roi", "profit factor", "win rate", "drawdown", "sharpe ratio", "profitability ranking")
    for name in required:
        text = (Path("reports") / name).read_text(encoding="utf-8").lower()
        assert not any(term in text for term in banned)


if __name__ == "__main__":
    test_framework_profiling_reports(); print("test_framework_profiling_reports passed")
