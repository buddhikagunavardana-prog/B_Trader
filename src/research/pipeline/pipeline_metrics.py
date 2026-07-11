import pandas as pd


def add_research_score_columns(report: pd.DataFrame) -> pd.DataFrame:
    scored = report.copy()
    scored["PF Score"] = scored["Profit Factor"].clip(0, 2) / 2 * 25
    scored["PnL Score"] = scored["Total PnL %"].clip(0, 50) / 50 * 25
    scored["Win Score"] = scored["Win Rate %"].clip(0, 60) / 60 * 20
    scored["DD Score"] = (
        1 - scored["Max Drawdown %"].abs().clip(0, 40) / 40
    ) * 20
    scored["Trade Score"] = scored["Trades"].clip(0, 200) / 200 * 10
    scored["Overall Score"] = (
        scored["PF Score"]
        + scored["PnL Score"]
        + scored["Win Score"]
        + scored["DD Score"]
        + scored["Trade Score"]
    )

    return scored
