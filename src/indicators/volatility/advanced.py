import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns, require_source
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.bollinger import calculate_bollinger


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def calculate_bollinger_band_width(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0,
) -> pd.Series:
    """Calculate normalized width from shared Bollinger components."""
    period = positive_int(period, "period")
    std_dev = positive_float(std_dev, "std_dev")
    require_columns(df, ["close"])
    upper, middle, lower = calculate_bollinger(df, period, std_dev)
    return _clean((upper - lower) / middle, "BOLLINGER_BAND_WIDTH")


def calculate_bollinger_percent_b(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0,
) -> pd.Series:
    """Calculate close position inside shared Bollinger components."""
    period = positive_int(period, "period")
    std_dev = positive_float(std_dev, "std_dev")
    require_columns(df, ["close"])
    upper, _, lower = calculate_bollinger(df, period, std_dev)
    return _clean((df["close"] - lower) / (upper - lower), "BOLLINGER_PERCENT_B")


def calculate_chandelier_exit(
    df: pd.DataFrame,
    period: int = 22,
    atr_period: int = 22,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series]:
    """Calculate long and short Chandelier Exit levels."""
    period = positive_int(period, "period")
    atr_period = positive_int(atr_period, "atr_period")
    multiplier = positive_float(multiplier, "multiplier")
    require_columns(df, ["high", "low", "close"])
    atr = calculate_atr(df, atr_period)
    long_exit = df["high"].rolling(period).max() - multiplier * atr
    short_exit = df["low"].rolling(period).min() + multiplier * atr
    return _clean(long_exit, "CHANDELIER_LONG"), _clean(short_exit, "CHANDELIER_SHORT")


def calculate_normalized_atr(
    df: pd.DataFrame, period: int = 14,
) -> pd.Series:
    """Calculate ATR as a percentage of closing price."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    return _clean(100.0 * calculate_atr(df, period) / df["close"], "NORMALIZED_ATR")


def calculate_ulcer_index(
    df: pd.DataFrame, period: int = 14, source: str = "close",
) -> pd.Series:
    """Calculate downside drawdown volatility over a rolling window."""
    period = positive_int(period, "period")
    require_source(df, source)
    peak = df[source].rolling(period).max()
    drawdown = 100.0 * (df[source] - peak) / peak
    return _clean(np.sqrt((drawdown**2).rolling(period).mean()), "ULCER_INDEX")


def calculate_mass_index(
    df: pd.DataFrame, ema_period: int = 9, sum_period: int = 25,
) -> pd.Series:
    """Calculate the Mass Index from double-smoothed candle ranges."""
    ema_period = positive_int(ema_period, "ema_period")
    sum_period = positive_int(sum_period, "sum_period")
    require_columns(df, ["high", "low"])
    candle_range = df["high"] - df["low"]
    first = candle_range.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    second = first.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    return _clean((first / second).rolling(sum_period).sum(), "MASS_INDEX")
