import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns, require_source
from src.indicators.volatility.atr import calculate_atr


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def calculate_rogers_satchell_volatility(
    df: pd.DataFrame, period: int = 20, annualization: float = 365.0,
) -> pd.Series:
    """Estimate drift-independent volatility from OHLC log ranges."""
    period = positive_int(period, "period")
    annualization = positive_float(annualization, "annualization")
    require_columns(df, ["open", "high", "low", "close"])
    variance = np.log(df["high"] / df["open"]) * np.log(df["high"] / df["close"]) + np.log(df["low"] / df["open"]) * np.log(df["low"] / df["close"])
    return _clean(np.sqrt(variance.rolling(period).mean().clip(lower=0.0) * annualization), "ROGERS_SATCHELL_VOLATILITY")


def calculate_yang_zhang_volatility(
    df: pd.DataFrame, period: int = 20, annualization: float = 365.0,
) -> pd.Series:
    """Estimate Yang-Zhang volatility from overnight, open-close, and range terms."""
    period = positive_int(period, "period")
    if period < 2:
        raise ValueError("period must be at least 2")
    annualization = positive_float(annualization, "annualization")
    require_columns(df, ["open", "high", "low", "close"])
    overnight = np.log(df["open"] / df["close"].shift())
    open_close = np.log(df["close"] / df["open"])
    rs = np.log(df["high"] / df["open"]) * np.log(df["high"] / df["close"]) + np.log(df["low"] / df["open"]) * np.log(df["low"] / df["close"])
    weight = 0.34 / (1.34 + (period + 1.0) / (period - 1.0))
    variance = overnight.rolling(period).var() + weight * open_close.rolling(period).var() + (1.0 - weight) * rs.rolling(period).mean()
    return _clean(np.sqrt(variance.clip(lower=0.0) * annualization), "YANG_ZHANG_VOLATILITY")


def calculate_close_to_close_volatility(
    df: pd.DataFrame, period: int = 20, annualization: float = 365.0, source: str = "close",
) -> pd.Series:
    """Calculate annualized rolling standard deviation of log close returns."""
    period = positive_int(period, "period")
    annualization = positive_float(annualization, "annualization")
    require_source(df, source)
    returns = np.log(df[source] / df[source].shift())
    return _clean(returns.rolling(period).std() * np.sqrt(annualization), "CLOSE_TO_CLOSE_VOLATILITY")


def calculate_median_absolute_deviation(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate rolling median absolute deviation from the window median."""
    period = positive_int(period, "period")
    require_source(df, source)
    values = df[source].astype(float).to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    if len(df) >= period:
        windows = np.lib.stride_tricks.sliding_window_view(values, period)
        medians = np.median(windows, axis=1)
        output[period - 1 :] = np.median(np.abs(windows - medians[:, None]), axis=1)
    return pd.Series(output, index=df.index, name="MEDIAN_ABSOLUTE_DEVIATION")


def calculate_average_daily_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the rolling arithmetic mean of each candle's high-low range."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    return _clean((df["high"] - df["low"]).rolling(period).mean(), "AVERAGE_DAILY_RANGE")


def calculate_relative_average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR as a percentage of closing price using shared ATR."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    return _clean(100.0 * calculate_atr(df, period) / df["close"], "RELATIVE_AVERAGE_TRUE_RANGE")


def calculate_coefficient_of_variation(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate rolling standard deviation as a percentage of rolling mean."""
    period = positive_int(period, "period")
    require_source(df, source)
    rolling = df[source].rolling(period)
    return _clean(100.0 * rolling.std() / rolling.mean(), "COEFFICIENT_OF_VARIATION")
