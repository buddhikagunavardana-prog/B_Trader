import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, require_columns


def calculate_parabolic_sar(
    df: pd.DataFrame,
    acceleration: float = 0.02,
    maximum: float = 0.2,
) -> tuple[pd.Series, pd.Series]:
    """Calculate causal Parabolic SAR values and trend direction."""
    acceleration = positive_float(acceleration, "acceleration")
    maximum = positive_float(maximum, "maximum")
    if maximum < acceleration:
        raise ValueError("maximum must be greater than or equal to acceleration")
    require_columns(df, ["high", "low"])

    high = df["high"].astype(float).to_numpy(copy=False)
    low = df["low"].astype(float).to_numpy(copy=False)
    sar = np.full(len(df), np.nan, dtype=float)
    direction = np.full(len(df), np.nan, dtype=float)
    if not len(df):
        return (
            pd.Series(sar, index=df.index, name="PARABOLIC_SAR"),
            pd.Series(direction, index=df.index, name="PARABOLIC_SAR_DIRECTION"),
        )

    uptrend = True
    extreme = np.nan
    factor = acceleration
    for index in range(len(df)):
        if not np.isfinite(high[index]) or not np.isfinite(low[index]):
            continue
        if index == 0 or not np.isfinite(sar[index - 1]):
            sar[index] = low[index]
            direction[index] = 1.0
            uptrend = True
            extreme = high[index]
            factor = acceleration
            continue

        candidate = sar[index - 1] + factor * (extreme - sar[index - 1])
        if uptrend:
            candidate = min(candidate, low[index - 1])
            if index > 1 and np.isfinite(low[index - 2]):
                candidate = min(candidate, low[index - 2])
            if low[index] < candidate:
                uptrend = False
                candidate = extreme
                extreme = low[index]
                factor = acceleration
            elif high[index] > extreme:
                extreme = high[index]
                factor = min(maximum, factor + acceleration)
        else:
            candidate = max(candidate, high[index - 1])
            if index > 1 and np.isfinite(high[index - 2]):
                candidate = max(candidate, high[index - 2])
            if high[index] > candidate:
                uptrend = True
                candidate = extreme
                extreme = high[index]
                factor = acceleration
            elif low[index] < extreme:
                extreme = low[index]
                factor = min(maximum, factor + acceleration)

        sar[index] = candidate
        direction[index] = 1.0 if uptrend else -1.0

    return (
        pd.Series(sar, index=df.index, name="PARABOLIC_SAR"),
        pd.Series(direction, index=df.index, name="PARABOLIC_SAR_DIRECTION"),
    )
