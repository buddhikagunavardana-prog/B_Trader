import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns, require_source
from src.indicators.momentum.advanced import calculate_cmo


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def calculate_linear_regression_trend(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Return the rolling regression value at the current candle."""
    period = positive_int(period, "period")
    require_source(df, source)
    x = np.arange(period, dtype=float)
    centered = x - x.mean()
    denominator = np.square(centered).sum()
    result = df[source].rolling(period).apply(
        lambda values: float(
            values.mean()
            + np.dot(centered, values) / denominator * (period - 1 - x.mean())
        ),
        raw=True,
    )
    return _clean(result, "LINEAR_REGRESSION_TREND")


def calculate_trima(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate a triangular moving average using two causal SMAs."""
    period = positive_int(period, "period")
    require_source(df, source)
    first = (period + 1) // 2
    second = period // 2 + 1
    return _clean(
        df[source].rolling(first).mean().rolling(second).mean(),
        "TRIMA",
    )


def calculate_alma(
    df: pd.DataFrame,
    period: int = 20,
    offset: float = 0.85,
    sigma: float = 6.0,
    source: str = "close",
) -> pd.Series:
    """Calculate the Arnaud Legoux Moving Average."""
    period = positive_int(period, "period")
    sigma = positive_float(sigma, "sigma")
    if isinstance(offset, bool) or not isinstance(offset, (int, float)) or not 0 <= offset <= 1:
        raise ValueError("offset must be between 0 and 1")
    require_source(df, source)
    positions = np.arange(period, dtype=float)
    center = offset * (period - 1)
    width = period / sigma
    weights = np.exp(-((positions - center) ** 2) / (2 * width**2))
    weights /= weights.sum()
    result = df[source].rolling(period).apply(
        lambda values: float(np.dot(values, weights)), raw=True,
    )
    return _clean(result, "ALMA")


def calculate_zlema(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate a zero-lag EMA from a de-lagged source series."""
    period = positive_int(period, "period")
    require_source(df, source)
    lag = max((period - 1) // 2, 1)
    adjusted = df[source] + df[source].diff(lag)
    return _clean(
        adjusted.ewm(span=period, adjust=False, min_periods=period).mean(),
        "ZLEMA",
    )


def calculate_mcginley_dynamic(
    df: pd.DataFrame, period: int = 14, source: str = "close",
) -> pd.Series:
    """Calculate the recursive McGinley Dynamic average."""
    period = positive_int(period, "period")
    require_source(df, source)
    price = df[source].astype(float).to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    if len(df) >= period:
        output[period - 1] = np.nanmean(price[:period])
        for index in range(period, len(df)):
            previous = output[index - 1]
            current = price[index]
            if not np.isfinite(previous) or not np.isfinite(current) or previous == 0:
                continue
            ratio = current / previous
            denominator = period * max(ratio**4, 1e-12)
            output[index] = previous + (current - previous) / denominator
    return pd.Series(output, index=df.index, name="MCGINLEY_DYNAMIC")


def calculate_frama(
    df: pd.DataFrame, period: int = 16, source: str = "close",
) -> pd.Series:
    """Calculate a causal Fractal Adaptive Moving Average."""
    period = positive_int(period, "period")
    if period < 4 or period % 2:
        raise ValueError("period must be an even integer of at least 4")
    require_columns(df, ["high", "low"])
    require_source(df, source)
    half = period // 2
    range_half = (
        df["high"].rolling(half).max() - df["low"].rolling(half).min()
    ) / half
    n1 = range_half
    n2 = range_half.shift(half)
    n3 = (
        df["high"].rolling(period).max() - df["low"].rolling(period).min()
    ) / period
    dimension = np.log((n1 + n2).where((n1 + n2) > 0)) - np.log(n3.where(n3 > 0))
    dimension /= np.log(2.0)
    alpha = np.exp(-4.6 * (dimension - 1.0)).clip(0.01, 1.0)
    price = df[source].astype(float).to_numpy(copy=False)
    factors = alpha.to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    if len(df) >= period:
        output[period - 1] = price[period - 1]
        for index in range(period, len(df)):
            if np.isfinite(price[index]) and np.isfinite(factors[index]):
                output[index] = factors[index] * price[index] + (1 - factors[index]) * output[index - 1]
    return pd.Series(output, index=df.index, name="FRAMA")


def calculate_vidya(
    df: pd.DataFrame,
    period: int = 14,
    momentum_period: int = 9,
    source: str = "close",
) -> pd.Series:
    """Calculate a CMO-weighted Variable Index Dynamic Average."""
    period = positive_int(period, "period")
    momentum_period = positive_int(momentum_period, "momentum_period")
    require_source(df, source)
    cmo = calculate_cmo(df, momentum_period, source).abs() / 100.0
    factors = (2.0 / (period + 1.0) * cmo).to_numpy(copy=False)
    price = df[source].astype(float).to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    start = max(period, momentum_period) - 1
    if len(df) > start:
        output[start] = np.nanmean(price[start - period + 1 : start + 1])
        for index in range(start + 1, len(df)):
            if np.isfinite(price[index]) and np.isfinite(factors[index]):
                output[index] = factors[index] * price[index] + (1 - factors[index]) * output[index - 1]
    return pd.Series(output, index=df.index, name="VIDYA")


def calculate_moving_average_envelope(
    df: pd.DataFrame,
    period: int = 20,
    percentage: float = 2.5,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate causal SMA envelopes around price."""
    period = positive_int(period, "period")
    percentage = positive_float(percentage, "percentage")
    require_source(df, source)
    middle = df[source].rolling(period).mean()
    fraction = percentage / 100.0
    return (
        _clean(middle * (1 + fraction), "MA_ENVELOPE_UPPER"),
        _clean(middle, "MA_ENVELOPE_MIDDLE"),
        _clean(middle * (1 - fraction), "MA_ENVELOPE_LOWER"),
    )


def calculate_linear_regression_slope(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate the rolling least-squares price slope."""
    period = positive_int(period, "period")
    require_source(df, source)
    x = np.arange(period, dtype=float)
    centered = x - x.mean()
    denominator = np.square(centered).sum()
    result = df[source].rolling(period).apply(
        lambda values: float(np.dot(centered, values - values.mean()) / denominator),
        raw=True,
    )
    return _clean(result, "LINEAR_REGRESSION_SLOPE")


def calculate_time_series_forecast(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Forecast the next value from a causal rolling regression."""
    period = positive_int(period, "period")
    require_source(df, source)
    x = np.arange(period, dtype=float)
    centered = x - x.mean()
    denominator = np.square(centered).sum()
    result = df[source].rolling(period).apply(
        lambda values: float(
            values.mean() + np.dot(centered, values) / denominator * (period - x.mean())
        ),
        raw=True,
    )
    return _clean(result, "TIME_SERIES_FORECAST")


def calculate_dpo(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate a causally aligned Detrended Price Oscillator."""
    period = positive_int(period, "period")
    require_source(df, source)
    lag = period // 2 + 1
    baseline = df[source].rolling(period).mean()
    return _clean(df[source].shift(lag) - baseline, "DPO")
