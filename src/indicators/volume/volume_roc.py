import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_volume_roc(df: pd.DataFrame, period: int = 12) -> pd.Series:
    period = positive_int(period, "period")
    require_columns(df, ["volume"])
    previous = df["volume"].shift(period)
    return (100.0 * (df["volume"] - previous) / previous).rename("VOLUME_ROC")
