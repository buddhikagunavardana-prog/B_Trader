import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_choppiness_index(df: pd.DataFrame, period: int = 14) -> pd.Series:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    range_span = df["high"].rolling(period).max() - df["low"].rolling(period).min()
    return (
        100.0 * np.log10(true_range.rolling(period).sum() / range_span) / np.log10(period)
    ).rename("CHOPPINESS_INDEX")
