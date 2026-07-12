import pandas as pd


RESEARCH_REPORT_COLUMNS = [
    "Strategy ID", "Strategy Name", "Role", "Status", "Net Profit", "ROI %",
    "Profit Factor", "Win Rate %", "Total Trades", "Max Drawdown %",
    "Expectancy", "Risk Adjusted Metric", "Walk Forward Efficiency",
    "Robustness Score", "Monte Carlo Survival", "Pair Consistency",
    "Regime Consistency", "Parameter Stability", "Portfolio Contribution",
    "Trade Frequency", "Average Holding Period", "Notes",
]


def empty_professional_research_report() -> pd.DataFrame:
    return pd.DataFrame(columns=RESEARCH_REPORT_COLUMNS)
