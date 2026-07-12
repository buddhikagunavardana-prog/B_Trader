import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_source


def calculate_kama(
    df: pd.DataFrame,
    period: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    source: str = "close",
) -> pd.Series:
    period = positive_int(period, "period")
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    require_source(df, source)
    price = df[source].astype(float)
    change = price.diff(period).abs()
    volatility = price.diff().abs().rolling(period).sum()
    efficiency = change.div(volatility.replace(0, np.nan)).fillna(0.0)
    fast = 2.0 / (fast_period + 1.0)
    slow = 2.0 / (slow_period + 1.0)
    smoothing = (efficiency * (fast - slow) + slow) ** 2
    values = price.to_numpy(copy=False)
    factors = smoothing.to_numpy(copy=False)
    output = np.full(len(price), np.nan, dtype=float)
    if len(output):
        output[0] = values[0]
        for index in range(1, len(output)):
            output[index] = output[index - 1] + factors[index] * (
                values[index] - output[index - 1]
            )
    return pd.Series(output, index=df.index, name="KAMA")
