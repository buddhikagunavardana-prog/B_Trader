import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns, require_source
from src.indicators.momentum.rsi import calculate_rsi
from src.indicators.volatility.atr import calculate_atr


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_dynamic_momentum_index(
    df: pd.DataFrame,
    volatility_period: int = 14,
    min_period: int = 5,
    max_period: int = 30,
    source: str = "close",
) -> pd.Series:
    """Calculate RSI with a causal period adapted by relative volatility."""
    for value, name in [(volatility_period, "volatility_period"), (min_period, "min_period"), (max_period, "max_period")]:
        positive_int(value, name)
    if min_period > max_period:
        raise ValueError("min_period must not exceed max_period")
    require_source(df, source)
    returns = df[source].pct_change()
    volatility = returns.rolling(volatility_period).std()
    baseline = volatility.rolling(volatility_period).mean()
    adaptive = (volatility / baseline).replace([np.inf, -np.inf], np.nan)
    periods = (max_period / adaptive).round().clip(min_period, max_period)
    changes = df[source].diff()
    candidates = []
    for period in range(min_period, max_period + 1):
        gains = changes.clip(lower=0).rolling(period).mean()
        losses = (-changes.clip(upper=0)).rolling(period).mean()
        relative = gains / losses
        candidates.append((100.0 - 100.0 / (1.0 + relative)).where(losses.ne(0), 100.0).where(gains.ne(0) | losses.ne(0), 50.0))
    matrix = np.column_stack([item.to_numpy(copy=False) for item in candidates])
    chosen = periods.to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    ready = np.isfinite(chosen)
    rows = np.flatnonzero(ready)
    output[rows] = matrix[rows, chosen[ready].astype(int) - min_period]
    return pd.Series(output, index=df.index, name="DYNAMIC_MOMENTUM_INDEX")


def calculate_laguerre_rsi(
    df: pd.DataFrame, gamma: float = 0.7, source: str = "close",
) -> pd.Series:
    """Calculate the causal four-stage Laguerre RSI oscillator."""
    if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not 0 < gamma < 1:
        raise ValueError("gamma must be between 0 and 1")
    require_source(df, source)
    price = df[source].astype(float).to_numpy(copy=False)
    output = np.full(len(df), np.nan)
    levels = np.zeros(4, dtype=float)
    for index, value in enumerate(price):
        if not np.isfinite(value):
            continue
        previous = levels.copy()
        levels[0] = (1 - gamma) * value + gamma * previous[0]
        levels[1] = -gamma * levels[0] + previous[0] + gamma * previous[1]
        levels[2] = -gamma * levels[1] + previous[1] + gamma * previous[2]
        levels[3] = -gamma * levels[2] + previous[2] + gamma * previous[3]
        if index < 3:
            continue
        up = sum(max(levels[i] - levels[i + 1], 0.0) for i in range(3))
        down = sum(max(levels[i + 1] - levels[i], 0.0) for i in range(3))
        output[index] = up / (up + down) if up + down else 0.5
    return pd.Series(output, index=df.index, name="LAGUERRE_RSI")


def calculate_inverse_fisher_rsi(
    df: pd.DataFrame, period: int = 14, smoothing_period: int = 9,
) -> pd.Series:
    """Transform shared RSI through a smoothed inverse Fisher function."""
    period = positive_int(period, "period")
    smoothing_period = positive_int(smoothing_period, "smoothing_period")
    require_columns(df, ["close"])
    rsi = calculate_rsi(df, period)
    scaled = 0.1 * (rsi - 50.0)
    smoothed = scaled.rolling(smoothing_period).mean()
    exponential = np.exp(2.0 * smoothed.clip(-20, 20))
    return _clean((exponential - 1.0) / (exponential + 1.0), "INVERSE_FISHER_RSI")


def calculate_correlation_trend_indicator(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Calculate rolling price correlation with chronological position."""
    period = positive_int(period, "period")
    require_source(df, source)
    positions = pd.Series(np.arange(len(df), dtype=float), index=df.index)
    result = df[source].rolling(period).corr(positions)
    return _clean(result, "CORRELATION_TREND_INDICATOR")


def calculate_trend_trigger_factor(df: pd.DataFrame, period: int = 15) -> pd.Series:
    """Calculate Trend Trigger Factor from adjacent causal price ranges."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    recent_high = df["high"].rolling(period).max()
    recent_low = df["low"].rolling(period).min()
    prior_high = recent_high.shift(period)
    prior_low = recent_low.shift(period)
    buy_power = recent_high - prior_low
    sell_power = prior_high - recent_low
    return _clean(200.0 * (buy_power - sell_power) / (buy_power + sell_power), "TREND_TRIGGER_FACTOR")


def calculate_wavetrend_oscillator(
    df: pd.DataFrame,
    channel_period: int = 10,
    average_period: int = 21,
    signal_period: int = 4,
) -> tuple[pd.Series, pd.Series]:
    """Calculate WaveTrend oscillator and its causal signal average."""
    for value, name in [(channel_period, "channel_period"), (average_period, "average_period"), (signal_period, "signal_period")]:
        positive_int(value, name)
    require_columns(df, ["high", "low", "close"])
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    esa = _ema(typical, channel_period)
    deviation = _ema((typical - esa).abs(), channel_period)
    wave = _ema((typical - esa) / (0.015 * deviation), average_period)
    return _clean(wave, "WAVETREND"), _clean(wave.rolling(signal_period).mean(), "WAVETREND_SIGNAL")


def calculate_squeeze_momentum(
    df: pd.DataFrame,
    period: int = 20,
    bollinger_multiplier: float = 2.0,
    keltner_multiplier: float = 1.5,
    source: str = "close",
) -> tuple[pd.Series, pd.Series]:
    """Calculate regression momentum and Bollinger-inside-Keltner squeeze state."""
    period = positive_int(period, "period")
    bollinger_multiplier = positive_float(bollinger_multiplier, "bollinger_multiplier")
    keltner_multiplier = positive_float(keltner_multiplier, "keltner_multiplier")
    require_columns(df, ["high", "low", "close"])
    require_source(df, source)
    middle = df[source].rolling(period).mean()
    deviation = df[source].rolling(period).std()
    atr = calculate_atr(df, period)
    squeeze = ((middle + bollinger_multiplier * deviation) < (middle + keltner_multiplier * atr)) & ((middle - bollinger_multiplier * deviation) > (middle - keltner_multiplier * atr))
    highest = df["high"].rolling(period).max()
    lowest = df["low"].rolling(period).min()
    detrended = df[source] - ((highest + lowest) / 2.0 + middle) / 2.0
    x = np.arange(period, dtype=float)
    centered = x - x.mean()
    denominator = np.square(centered).sum()
    values = detrended.to_numpy(copy=False)
    regression = np.full(len(df), np.nan)
    if len(df) >= period:
        windows = np.lib.stride_tricks.sliding_window_view(values, period)
        regression[period - 1 :] = windows.mean(axis=1) + windows.dot(centered) / denominator * (period - 1 - x.mean())
    momentum = pd.Series(regression, index=df.index)
    ready = deviation.notna() & atr.notna()
    return _clean(momentum, "SQUEEZE_MOMENTUM"), squeeze.astype(float).where(ready).rename("SQUEEZE_ON")


def calculate_cycle_identifier(
    df: pd.DataFrame, period: int = 20, source: str = "close",
) -> pd.Series:
    """Approximate cycle strength using causal detrended lag autocorrelation."""
    period = positive_int(period, "period")
    if period < 4:
        raise ValueError("period must be at least 4")
    require_source(df, source)
    detrended = df[source] - df[source].rolling(period).mean()
    result = detrended.rolling(period).corr(detrended.shift(period // 2))
    return _clean(result, "CYCLE_IDENTIFIER")
