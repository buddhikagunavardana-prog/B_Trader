import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns
from src.indicators.volatility.atr import calculate_atr


def calculate_supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series]:
    period = positive_int(period, "period")
    multiplier = positive_float(multiplier, "multiplier")
    require_columns(df, ["high", "low", "close"])
    atr = calculate_atr(df, period)
    midpoint = (df["high"] + df["low"]) / 2.0
    upper = midpoint + multiplier * atr
    lower = midpoint - multiplier * atr
    close = df["close"].to_numpy(copy=False)
    final_upper = upper.to_numpy(copy=True)
    final_lower = lower.to_numpy(copy=True)
    trend = np.ones(len(df), dtype=np.int8)
    line = np.full(len(df), np.nan, dtype=float)
    for index in range(1, len(df)):
        if np.isnan(final_upper[index - 1]) or np.isnan(final_lower[index - 1]):
            continue
        if close[index - 1] <= final_upper[index - 1]:
            final_upper[index] = min(final_upper[index], final_upper[index - 1])
        if close[index - 1] >= final_lower[index - 1]:
            final_lower[index] = max(final_lower[index], final_lower[index - 1])
        if close[index] > final_upper[index - 1]:
            trend[index] = 1
        elif close[index] < final_lower[index - 1]:
            trend[index] = -1
        else:
            trend[index] = trend[index - 1]
        line[index] = final_lower[index] if trend[index] == 1 else final_upper[index]
    return (
        pd.Series(line, index=df.index, name="SUPERTREND"),
        pd.Series(trend, index=df.index, name="SUPERTREND_DIRECTION"),
    )
