import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_rolling_vwap(df: pd.DataFrame, period: int = 96) -> pd.Series:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close", "volume"])
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    numerator = (typical * df["volume"]).rolling(period).sum()
    denominator = df["volume"].rolling(period).sum()
    return (numerator / denominator).rename("ROLLING_VWAP")
