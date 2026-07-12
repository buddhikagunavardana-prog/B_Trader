import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_ultimate_oscillator(
    df: pd.DataFrame,
    short_period: int = 7,
    medium_period: int = 14,
    long_period: int = 28,
) -> pd.Series:
    periods = [
        positive_int(short_period, "short_period"),
        positive_int(medium_period, "medium_period"),
        positive_int(long_period, "long_period"),
    ]
    if periods != sorted(periods) or len(set(periods)) != 3:
        raise ValueError("oscillator periods must be unique and increasing")
    require_columns(df, ["high", "low", "close"])
    previous_close = df["close"].shift()
    buying_pressure = df["close"] - pd.concat(
        [df["low"], previous_close], axis=1,
    ).min(axis=1)
    true_range = pd.concat([df["high"], previous_close], axis=1).max(axis=1) - pd.concat(
        [df["low"], previous_close], axis=1,
    ).min(axis=1)
    averages = [
        buying_pressure.rolling(period).sum() / true_range.rolling(period).sum()
        for period in periods
    ]
    return (100.0 * (4 * averages[0] + 2 * averages[1] + averages[2]) / 7).rename(
        "ULTIMATE_OSCILLATOR",
    )
