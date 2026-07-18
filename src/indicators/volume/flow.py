import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns, require_source
from src.indicators.volume.rolling_vwap import calculate_rolling_vwap


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def _money_flow_volume(df: pd.DataFrame) -> pd.Series:
    candle_range = (df["high"] - df["low"]).replace(0, np.nan)
    multiplier = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / candle_range
    return multiplier.fillna(0.0) * df["volume"]


def _klinger_volume_force(df: pd.DataFrame) -> pd.Series:
    typical = df["high"] + df["low"] + df["close"]
    trend = np.sign(typical.diff()).replace(0, np.nan).ffill().fillna(1.0).to_numpy()
    movement = (df["high"] - df["low"]).to_numpy(copy=False)
    cumulative = np.full(len(df), np.nan)
    if len(df):
        cumulative[0] = movement[0]
        for index in range(1, len(df)):
            if trend[index] == trend[index - 1]:
                cumulative[index] = cumulative[index - 1] + movement[index]
            else:
                cumulative[index] = movement[index - 1] + movement[index]
    ratio = np.full(len(df), np.nan)
    np.divide(2.0 * movement, cumulative, out=ratio, where=cumulative != 0)
    ratio -= 1.0
    force = df["volume"].to_numpy(copy=False) * trend * np.abs(ratio) * 100.0
    return pd.Series(force, index=df.index).replace([np.inf, -np.inf], np.nan)


def calculate_klinger_oscillator(
    df: pd.DataFrame,
    fast_period: int = 34,
    slow_period: int = 55,
    signal_period: int = 13,
) -> tuple[pd.Series, pd.Series]:
    """Calculate Klinger Volume Oscillator and signal."""
    for value, name in [(fast_period, "fast_period"), (slow_period, "slow_period"), (signal_period, "signal_period")]:
        positive_int(value, name)
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_columns(df, ["high", "low", "close", "volume"])
    force = _klinger_volume_force(df)
    oscillator = _ema(force, fast_period) - _ema(force, slow_period)
    return _clean(oscillator, "KLINGER_OSCILLATOR"), _clean(_ema(oscillator, signal_period), "KLINGER_SIGNAL")


def calculate_price_volume_trend(df: pd.DataFrame, source: str = "close") -> pd.Series:
    """Calculate cumulative Price Volume Trend (also called VPT)."""
    require_columns(df, ["volume"])
    require_source(df, source)
    contribution = df["volume"] * df[source].pct_change()
    return _clean(contribution.fillna(0.0).cumsum(), "PRICE_VOLUME_TREND")


def calculate_volume_oscillator(
    df: pd.DataFrame, fast_period: int = 14, slow_period: int = 28,
) -> pd.Series:
    """Calculate percentage difference between fast and slow volume EMAs."""
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_columns(df, ["volume"])
    fast = _ema(df["volume"], fast_period)
    slow = _ema(df["volume"], slow_period)
    return _clean(100.0 * (fast - slow) / slow, "VOLUME_OSCILLATOR")


def calculate_twiggs_money_flow(df: pd.DataFrame, period: int = 21) -> pd.Series:
    """Calculate exponentially smoothed Twiggs Money Flow."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close", "volume"])
    previous_close = df["close"].shift()
    true_high = pd.concat([df["high"], previous_close], axis=1).max(axis=1)
    true_low = pd.concat([df["low"], previous_close], axis=1).min(axis=1)
    range_ = (true_high - true_low).replace(0, np.nan)
    multiplier = ((df["close"] - true_low) - (true_high - df["close"])) / range_
    numerator = _ema(multiplier * df["volume"], period)
    denominator = _ema(df["volume"], period)
    return _clean(numerator / denominator, "TWIGGS_MONEY_FLOW")


def calculate_volume_weighted_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD from volume-weighted exponential averages."""
    for value, name in [(fast_period, "fast_period"), (slow_period, "slow_period"), (signal_period, "signal_period")]:
        positive_int(value, name)
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_columns(df, ["volume"])
    require_source(df, source)

    def vwema(period: int) -> pd.Series:
        return _ema(df[source] * df["volume"], period) / _ema(df["volume"], period)

    macd = vwema(fast_period) - vwema(slow_period)
    signal = _ema(macd, signal_period)
    return (
        _clean(macd, "VOLUME_WEIGHTED_MACD"),
        _clean(signal, "VOLUME_WEIGHTED_MACD_SIGNAL"),
        _clean(macd - signal, "VOLUME_WEIGHTED_MACD_HISTOGRAM"),
    )


def calculate_intraday_intensity_index(df: pd.DataFrame) -> pd.Series:
    """Calculate cumulative volume-normalized intraday intensity."""
    require_columns(df, ["high", "low", "close", "volume"])
    flow = _money_flow_volume(df)
    return _clean(100.0 * flow.cumsum() / df["volume"].cumsum(), "INTRADAY_INTENSITY_INDEX")


def calculate_money_flow_volume(df: pd.DataFrame) -> pd.Series:
    """Calculate the single-candle money-flow-volume component of ADL."""
    require_columns(df, ["high", "low", "close", "volume"])
    return _clean(_money_flow_volume(df), "MONEY_FLOW_VOLUME")


def calculate_volume_zone_oscillator(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate signed-volume pressure relative to total volume."""
    period = positive_int(period, "period")
    require_columns(df, ["close", "volume"])
    direction = np.sign(df["close"].diff())
    signed_volume = direction * df["volume"]
    return _clean(100.0 * _ema(signed_volume, period) / _ema(df["volume"], period), "VOLUME_ZONE_OSCILLATOR")


def calculate_net_volume(df: pd.DataFrame) -> pd.Series:
    """Calculate signed volume from close-to-close direction."""
    require_columns(df, ["close", "volume"])
    direction = np.sign(df["close"].diff())
    return _clean(direction * df["volume"], "NET_VOLUME")


def calculate_vwap_deviation(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate percentage price deviation from rolling VWAP."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close", "volume"])
    require_source(df, source)
    vwap = calculate_rolling_vwap(df, period)
    return _clean(100.0 * (df[source] - vwap) / vwap, "VWAP_DEVIATION")


def calculate_money_flow_oscillator(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate normalized positive-minus-negative raw money flow."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close", "volume"])
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    raw = typical * df["volume"]
    positive = raw.where(typical.diff() > 0, 0.0).rolling(period).sum()
    negative = raw.where(typical.diff() < 0, 0.0).rolling(period).sum()
    return _clean(100.0 * (positive - negative) / (positive + negative), "MONEY_FLOW_OSCILLATOR")
