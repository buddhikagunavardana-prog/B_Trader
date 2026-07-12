import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_price_channels(
    df: pd.DataFrame,
    period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    upper = df["high"].rolling(period).max().rename("PRICE_CHANNEL_UPPER")
    lower = df["low"].rolling(period).min().rename("PRICE_CHANNEL_LOWER")
    middle = ((upper + lower) / 2.0).rename("PRICE_CHANNEL_MIDDLE")
    return upper, middle, lower
