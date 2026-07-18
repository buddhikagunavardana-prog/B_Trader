import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_source


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_t3_moving_average(
    df: pd.DataFrame, period: int = 5, volume_factor: float = 0.7, source: str = "close",
) -> pd.Series:
    """Calculate Tillson's six-stage T3 moving average."""
    period = positive_int(period, "period")
    if isinstance(volume_factor, bool) or not isinstance(volume_factor, (int, float)) or not 0 <= volume_factor <= 1:
        raise ValueError("volume_factor must be between 0 and 1")
    require_source(df, source)
    e1 = _ema(df[source], period)
    e2 = _ema(e1, period)
    e3 = _ema(e2, period)
    e4 = _ema(e3, period)
    e5 = _ema(e4, period)
    e6 = _ema(e5, period)
    factor = float(volume_factor)
    c1 = -(factor**3)
    c2 = 3 * factor**2 + 3 * factor**3
    c3 = -6 * factor**2 - 3 * factor - 3 * factor**3
    c4 = 1 + 3 * factor + factor**3 + 3 * factor**2
    return _clean(c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3, "T3_MOVING_AVERAGE")


def calculate_jurik_moving_average_approximation(
    df: pd.DataFrame,
    period: int = 14,
    phase: float = 0.0,
    power: float = 2.0,
    source: str = "close",
) -> pd.Series:
    """Approximate JMA with a causal volatility-adaptive recursive smoother."""
    period = positive_int(period, "period")
    power = positive_float(power, "power")
    if isinstance(phase, bool) or not isinstance(phase, (int, float)) or not -100 <= phase <= 100:
        raise ValueError("phase must be between -100 and 100")
    require_source(df, source)
    price = df[source].astype(float).to_numpy(copy=False)
    volatility = df[source].diff().abs().rolling(period).mean().to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    if len(df) >= period:
        output[period - 1] = np.nanmean(price[:period])
        phase_ratio = float(phase) / 100.0
        base = 2.0 / (period + 1.0)
        for index in range(period, len(df)):
            if not np.isfinite(price[index]) or not np.isfinite(output[index - 1]):
                continue
            local = abs(price[index] - price[index - 1])
            ratio = local / volatility[index] if np.isfinite(volatility[index]) and volatility[index] > 0 else 1.0
            alpha = min(max(base * ratio**power, base / 4.0), 1.0)
            smoothed = output[index - 1] + alpha * (price[index] - output[index - 1])
            output[index] = smoothed + phase_ratio * alpha * (smoothed - output[index - 1])
    return pd.Series(output, index=df.index, name="JURIK_MOVING_AVERAGE_APPROXIMATION")


def calculate_double_smoothed_ema(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate an EMA smoothed by a second EMA of equal length."""
    period = positive_int(period, "period")
    require_source(df, source)
    return _clean(_ema(_ema(df[source], period), period), "DOUBLE_SMOOTHED_EMA")


def calculate_triple_smoothed_ema(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate an EMA smoothed by three equal-length EMA stages."""
    period = positive_int(period, "period")
    require_source(df, source)
    return _clean(_ema(_ema(_ema(df[source], period), period), period), "TRIPLE_SMOOTHED_EMA")


def calculate_gaussian_moving_average(
    df: pd.DataFrame, period: int = 20, sigma: float = 6.0, source: str = "close",
) -> pd.Series:
    """Calculate a causal Gaussian-weighted moving average."""
    period = positive_int(period, "period")
    sigma = positive_float(sigma, "sigma")
    require_source(df, source)
    positions = np.arange(period, dtype=float)
    weights = np.exp(-0.5 * ((positions - (period - 1)) / (period / sigma)) ** 2)
    weights /= weights.sum()
    result = df[source].rolling(period).apply(lambda values: float(np.dot(values, weights)), raw=True)
    return _clean(result, "GAUSSIAN_MOVING_AVERAGE")


def calculate_ehlers_super_smoother(
    df: pd.DataFrame, period: int = 10, source: str = "close",
) -> pd.Series:
    """Approximate Ehlers' causal two-pole Super Smoother filter."""
    period = positive_int(period, "period")
    if period < 3:
        raise ValueError("period must be at least 3")
    require_source(df, source)
    price = df[source].astype(float).to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    a1 = np.exp(-np.sqrt(2.0) * np.pi / period)
    b1 = 2.0 * a1 * np.cos(np.sqrt(2.0) * np.pi / period)
    c2, c3 = b1, -(a1**2)
    c1 = 1.0 - c2 - c3
    if len(df) >= period:
        output[period - 1] = np.nanmean(price[:period])
        if len(df) > period:
            output[period] = output[period - 1]
        for index in range(period + 1, len(df)):
            if np.isfinite(price[index]) and np.isfinite(price[index - 1]):
                output[index] = c1 * (price[index] + price[index - 1]) / 2.0 + c2 * output[index - 1] + c3 * output[index - 2]
    return pd.Series(output, index=df.index, name="EHLERS_SUPER_SMOOTHER")


def calculate_ehlers_roofing_filter(
    df: pd.DataFrame,
    high_pass_period: int = 48,
    smooth_period: int = 10,
    source: str = "close",
) -> pd.Series:
    """Approximate Ehlers Roofing Filter with causal high-pass and smoothing stages."""
    high_pass_period = positive_int(high_pass_period, "high_pass_period")
    smooth_period = positive_int(smooth_period, "smooth_period")
    if high_pass_period < 3 or smooth_period < 3:
        raise ValueError("filter periods must be at least 3")
    require_source(df, source)
    price = df[source].astype(float).to_numpy(copy=False)
    high_pass = np.full(len(df), np.nan)
    angle = np.sqrt(2.0) * np.pi / high_pass_period
    alpha = (np.cos(angle) + np.sin(angle) - 1.0) / np.cos(angle)
    start = max(high_pass_period - 1, 2)
    for index in range(start, len(df)):
        previous1 = 0.0 if not np.isfinite(high_pass[index - 1]) else high_pass[index - 1]
        previous2 = 0.0 if not np.isfinite(high_pass[index - 2]) else high_pass[index - 2]
        high_pass[index] = (1 - alpha / 2) ** 2 * (price[index] - 2 * price[index - 1] + price[index - 2]) + 2 * (1 - alpha) * previous1 - (1 - alpha) ** 2 * previous2
    smoothed = pd.Series(high_pass, index=df.index).ewm(
        span=smooth_period, adjust=False, min_periods=smooth_period,
    ).mean()
    return _clean(smoothed, "EHLERS_ROOFING_FILTER")


def calculate_sine_weighted_moving_average(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate a causal sine-weighted moving average."""
    period = positive_int(period, "period")
    require_source(df, source)
    weights = np.sin(np.pi * (np.arange(period, dtype=float) + 1.0) / (period + 1.0))
    weights /= weights.sum()
    result = df[source].rolling(period).apply(lambda values: float(np.dot(values, weights)), raw=True)
    return _clean(result, "SINE_WEIGHTED_MOVING_AVERAGE")
