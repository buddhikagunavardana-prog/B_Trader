import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns, require_source
from src.indicators.volume.adl import calculate_adl


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def calculate_force_index(
    df: pd.DataFrame,
    period: int = 1,
    smoothing_period: int = 13,
    source: str = "close",
) -> pd.Series:
    """Calculate an EMA-smoothed Force Index."""
    period = positive_int(period, "period")
    smoothing_period = positive_int(smoothing_period, "smoothing_period")
    require_columns(df, ["volume"])
    require_source(df, source)
    raw = df[source].diff(period) * df["volume"]
    return _clean(
        raw.ewm(span=smoothing_period, adjust=False, min_periods=smoothing_period).mean(),
        "FORCE_INDEX",
    )


def calculate_volume_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate an exponential moving average of volume."""
    period = positive_int(period, "period")
    require_columns(df, ["volume"])
    return _clean(
        df["volume"].ewm(span=period, adjust=False, min_periods=period).mean(),
        "VOLUME_EMA",
    )


def calculate_chaikin_oscillator(
    df: pd.DataFrame, fast_period: int = 3, slow_period: int = 10,
) -> pd.Series:
    """Calculate the Chaikin Oscillator from a shared ADL series."""
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_columns(df, ["high", "low", "close", "volume"])
    adl = calculate_adl(df)
    fast = adl.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
    slow = adl.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
    return _clean(fast - slow, "CHAIKIN_OSCILLATOR")


def _volume_index(
    df: pd.DataFrame, use_increases: bool, initial_value: float, name: str,
) -> pd.Series:
    close_change = df["close"].pct_change().replace([np.inf, -np.inf], np.nan)
    volume_change = df["volume"].diff()
    active = volume_change.gt(0) if use_increases else volume_change.lt(0)
    output = np.full(len(df), np.nan)
    if len(df):
        output[0] = initial_value
        changes = close_change.to_numpy(copy=False)
        mask = active.to_numpy(copy=False)
        for index in range(1, len(df)):
            output[index] = output[index - 1]
            if mask[index] and np.isfinite(changes[index]):
                output[index] *= 1.0 + changes[index]
    return pd.Series(output, index=df.index, name=name)


def calculate_negative_volume_index(
    df: pd.DataFrame, initial_value: float = 1000.0,
) -> pd.Series:
    """Update a cumulative price index only when volume decreases."""
    if isinstance(initial_value, bool) or not isinstance(initial_value, (int, float)) or initial_value <= 0:
        raise ValueError("initial_value must be positive")
    require_columns(df, ["close", "volume"])
    return _volume_index(df, False, float(initial_value), "NEGATIVE_VOLUME_INDEX")


def calculate_positive_volume_index(
    df: pd.DataFrame, initial_value: float = 1000.0,
) -> pd.Series:
    """Update a cumulative price index only when volume increases."""
    if isinstance(initial_value, bool) or not isinstance(initial_value, (int, float)) or initial_value <= 0:
        raise ValueError("initial_value must be positive")
    require_columns(df, ["close", "volume"])
    return _volume_index(df, True, float(initial_value), "POSITIVE_VOLUME_INDEX")
