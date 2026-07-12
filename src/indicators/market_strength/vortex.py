import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_vortex(
    df: pd.DataFrame,
    period: int = 14,
) -> tuple[pd.Series, pd.Series]:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1).rolling(period).sum()
    positive = (df["high"] - df["low"].shift()).abs().rolling(period).sum()
    negative = (df["low"] - df["high"].shift()).abs().rolling(period).sum()
    return (positive / true_range).rename("VORTEX_POSITIVE"), (
        negative / true_range
    ).rename("VORTEX_NEGATIVE")
