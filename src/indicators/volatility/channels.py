import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns, require_source
from src.indicators.trend.ema import calculate_ema
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.donchian import calculate_donchian_channel
from src.indicators.volatility.keltner import calculate_keltner_channel


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def calculate_true_range(df: pd.DataFrame) -> pd.Series:
    """Calculate one-period True Range."""
    require_columns(df, ["high", "low", "close"])
    previous_close = df["close"].shift()
    result = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _clean(result, "TRUE_RANGE")


def calculate_volatility_stop(
    df: pd.DataFrame,
    period: int = 20,
    atr_period: int = 14,
    multiplier: float = 2.0,
    source: str = "close",
) -> tuple[pd.Series, pd.Series]:
    """Calculate close-extrema volatility stops using ATR."""
    period = positive_int(period, "period")
    atr_period = positive_int(atr_period, "atr_period")
    multiplier = positive_float(multiplier, "multiplier")
    require_columns(df, ["high", "low", "close"])
    require_source(df, source)
    atr = calculate_atr(df, atr_period)
    long_stop = df[source].rolling(period).max() - multiplier * atr
    short_stop = df[source].rolling(period).min() + multiplier * atr
    return _clean(long_stop, "VOLATILITY_STOP_LONG"), _clean(short_stop, "VOLATILITY_STOP_SHORT")


def calculate_atr_bands(
    df: pd.DataFrame,
    period: int = 20,
    atr_period: int = 14,
    multiplier: float = 2.0,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate EMA-centered ATR bands."""
    period = positive_int(period, "period")
    atr_period = positive_int(atr_period, "atr_period")
    multiplier = positive_float(multiplier, "multiplier")
    require_columns(df, ["high", "low", "close"])
    require_source(df, source)
    middle = calculate_ema(df, period, source).where(df[source].rolling(period).count().eq(period))
    atr = calculate_atr(df, atr_period)
    return (
        _clean(middle + multiplier * atr, "ATR_UPPER_BAND"),
        _clean(middle, "ATR_MIDDLE_BAND"),
        _clean(middle - multiplier * atr, "ATR_LOWER_BAND"),
    )


def calculate_fractal_chaos_bands(
    df: pd.DataFrame, period: int = 2,
) -> tuple[pd.Series, pd.Series]:
    """Publish confirmed fractal extrema after the right-side delay."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    window = 2 * period + 1
    candidate_high = df["high"].shift(period)
    candidate_low = df["low"].shift(period)
    confirmed_high = candidate_high.where(candidate_high.eq(df["high"].rolling(window).max()))
    confirmed_low = candidate_low.where(candidate_low.eq(df["low"].rolling(window).min()))
    ready = df["high"].rolling(window).count().eq(window)
    upper = confirmed_high.ffill().where(ready)
    lower = confirmed_low.ffill().where(ready)
    return _clean(upper, "FRACTAL_CHAOS_UPPER"), _clean(lower, "FRACTAL_CHAOS_LOWER")


def calculate_moving_std_channel(
    df: pd.DataFrame,
    period: int = 20,
    multiplier: float = 2.0,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate moving-average bands from rolling standard deviation."""
    period = positive_int(period, "period")
    multiplier = positive_float(multiplier, "multiplier")
    require_source(df, source)
    middle = df[source].rolling(period).mean()
    deviation = df[source].rolling(period).std()
    return (
        _clean(middle + multiplier * deviation, "MOVING_STD_UPPER"),
        _clean(middle, "MOVING_STD_MIDDLE"),
        _clean(middle - multiplier * deviation, "MOVING_STD_LOWER"),
    )


def calculate_donchian_width(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate normalized width from shared Donchian components."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    upper, middle, lower = calculate_donchian_channel(df, period)
    return _clean((upper - lower) / middle, "DONCHIAN_WIDTH")


def calculate_keltner_width(
    df: pd.DataFrame,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> pd.Series:
    """Calculate normalized width from shared Keltner components."""
    ema_period = positive_int(ema_period, "ema_period")
    atr_period = positive_int(atr_period, "atr_period")
    multiplier = positive_float(multiplier, "multiplier")
    require_columns(df, ["high", "low", "close"])
    upper, middle, lower = calculate_keltner_channel(df, ema_period, atr_period, multiplier)
    return _clean((upper - lower) / middle, "KELTNER_WIDTH")


def calculate_parkinson_volatility(
    df: pd.DataFrame, period: int = 20, annualization: float = 365.0,
) -> pd.Series:
    """Estimate volatility from rolling high-low log ranges."""
    period = positive_int(period, "period")
    annualization = positive_float(annualization, "annualization")
    require_columns(df, ["high", "low"])
    log_range = np.log(df["high"] / df["low"])
    variance = log_range.pow(2).rolling(period).mean() / (4.0 * np.log(2.0))
    return _clean(np.sqrt(variance * annualization), "PARKINSON_VOLATILITY")


def calculate_garman_klass_volatility(
    df: pd.DataFrame, period: int = 20, annualization: float = 365.0,
) -> pd.Series:
    """Estimate volatility from OHLC log ranges."""
    period = positive_int(period, "period")
    annualization = positive_float(annualization, "annualization")
    require_columns(df, ["open", "high", "low", "close"])
    high_low = np.log(df["high"] / df["low"])
    close_open = np.log(df["close"] / df["open"])
    variance = (
        0.5 * high_low.pow(2) - (2.0 * np.log(2.0) - 1.0) * close_open.pow(2)
    ).rolling(period).mean().clip(lower=0.0)
    return _clean(np.sqrt(variance * annualization), "GARMAN_KLASS_VOLATILITY")
