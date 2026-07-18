import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_swing_points(
    df: pd.DataFrame,
    period: int = 5,
) -> tuple[pd.Series, pd.Series]:
    """Flag confirmed swing points without reading future rows."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    window = period * 2 + 1
    candidate_high = df["high"].shift(period)
    candidate_low = df["low"].shift(period)
    swing_high = candidate_high.eq(df["high"].rolling(window).max()).rename(
        "SWING_HIGH",
    )
    swing_low = candidate_low.eq(df["low"].rolling(window).min()).rename(
        "SWING_LOW",
    )
    return swing_high, swing_low
