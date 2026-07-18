import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns, require_source
from src.indicators.momentum.advanced import calculate_awesome_oscillator
from src.indicators.momentum.roc import calculate_roc
from src.indicators.trend.advanced import calculate_linear_regression_trend
from src.indicators.volatility.atr import calculate_atr


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_accelerator_oscillator(
    df: pd.DataFrame, fast_period: int = 5, slow_period: int = 34, signal_period: int = 5,
) -> pd.Series:
    """Calculate Awesome Oscillator minus its signal average."""
    signal_period = positive_int(signal_period, "signal_period")
    awesome = calculate_awesome_oscillator(df, fast_period, slow_period)
    return _clean(awesome - awesome.rolling(signal_period).mean(), "ACCELERATOR_OSCILLATOR")


def calculate_schaff_trend_cycle(
    df: pd.DataFrame,
    fast_period: int = 23,
    slow_period: int = 50,
    cycle_period: int = 10,
    smoothing_period: int = 3,
    source: str = "close",
) -> pd.Series:
    """Calculate a causally smoothed stochastic cycle of MACD."""
    for value, name in [(fast_period, "fast_period"), (slow_period, "slow_period"), (cycle_period, "cycle_period"), (smoothing_period, "smoothing_period")]:
        positive_int(value, name)
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_source(df, source)
    macd = _ema(df[source], fast_period) - _ema(df[source], slow_period)
    lowest = macd.rolling(cycle_period).min()
    highest = macd.rolling(cycle_period).max()
    stochastic = 100.0 * (macd - lowest) / (highest - lowest)
    first = _ema(stochastic, smoothing_period)
    lowest_first = first.rolling(cycle_period).min()
    highest_first = first.rolling(cycle_period).max()
    second = 100.0 * (first - lowest_first) / (highest_first - lowest_first)
    return _clean(_ema(second, smoothing_period), "SCHAFF_TREND_CYCLE")


def calculate_kst(
    df: pd.DataFrame,
    roc1_period: int = 10,
    roc2_period: int = 15,
    roc3_period: int = 20,
    roc4_period: int = 30,
    signal_period: int = 9,
    source: str = "close",
) -> tuple[pd.Series, pd.Series]:
    """Calculate Know Sure Thing and its signal from shared ROC components."""
    periods = [positive_int(value, name) for value, name in [(roc1_period, "roc1_period"), (roc2_period, "roc2_period"), (roc3_period, "roc3_period"), (roc4_period, "roc4_period")]]
    signal_period = positive_int(signal_period, "signal_period")
    require_source(df, source)
    smooth_periods = [10, 10, 10, 15]
    components = [
        calculate_roc(df, period, source).rolling(smoothing).mean()
        for period, smoothing in zip(periods, smooth_periods)
    ]
    kst = components[0] + 2 * components[1] + 3 * components[2] + 4 * components[3]
    return _clean(kst, "KST"), _clean(kst.rolling(signal_period).mean(), "KST_SIGNAL")


def calculate_smi_ergodic(
    df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 13,
    source: str = "close",
) -> tuple[pd.Series, pd.Series]:
    """Calculate the SMI Ergodic oscillator and signal."""
    for value, name in [(long_period, "long_period"), (short_period, "short_period"), (signal_period, "signal_period")]:
        positive_int(value, name)
    require_source(df, source)
    momentum = df[source].diff()
    numerator = _ema(_ema(momentum, long_period), short_period)
    denominator = _ema(_ema(momentum.abs(), long_period), short_period)
    smi = 100.0 * numerator / denominator
    signal = _ema(smi, signal_period)
    return _clean(smi, "SMI_ERGODIC"), _clean(signal, "SMI_ERGODIC_SIGNAL")


def calculate_demarker(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate DeMarker from directional high and low changes."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    demax = df["high"].diff().clip(lower=0).rolling(period).sum()
    demin = (-df["low"].diff()).clip(lower=0).rolling(period).sum()
    return _clean(demax / (demax + demin), "DEMARKER")


def calculate_qstick(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the rolling average candle body."""
    period = positive_int(period, "period")
    require_columns(df, ["open", "close"])
    return _clean((df["close"] - df["open"]).rolling(period).mean(), "QSTICK")


def calculate_relative_vigor_index(
    df: pd.DataFrame, period: int = 10, signal_period: int = 4,
) -> tuple[pd.Series, pd.Series]:
    """Calculate Relative Vigor Index and its signal."""
    period = positive_int(period, "period")
    signal_period = positive_int(signal_period, "signal_period")
    require_columns(df, ["open", "high", "low", "close"])
    vigor = (df["close"] - df["open"]).rolling(period).mean() / (
        (df["high"] - df["low"]).rolling(period).mean()
    )
    return _clean(vigor, "RELATIVE_VIGOR"), _clean(vigor.rolling(signal_period).mean(), "RELATIVE_VIGOR_SIGNAL")


def calculate_center_of_gravity(
    df: pd.DataFrame, period: int = 10, source: str = "close",
) -> pd.Series:
    """Calculate Ehlers-style Center of Gravity oscillator."""
    period = positive_int(period, "period")
    require_source(df, source)
    weights = np.arange(1, period + 1, dtype=float)
    result = df[source].rolling(period).apply(
        lambda values: float(-np.dot(values, weights) / values.sum()), raw=True,
    )
    return _clean(result + (period + 1) / 2.0, "CENTER_OF_GRAVITY")


def calculate_chande_forecast_oscillator(
    df: pd.DataFrame, period: int = 14, source: str = "close",
) -> pd.Series:
    """Calculate price distance from rolling regression as a percentage."""
    period = positive_int(period, "period")
    require_source(df, source)
    forecast = calculate_linear_regression_trend(df, period, source)
    return _clean(100.0 * (df[source] - forecast) / df[source], "CHANDE_FORECAST_OSCILLATOR")


def calculate_pretty_good_oscillator(
    df: pd.DataFrame, period: int = 14, source: str = "close",
) -> pd.Series:
    """Calculate price distance from SMA normalized by ATR."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    require_source(df, source)
    average = df[source].rolling(period).mean()
    return _clean((df[source] - average) / calculate_atr(df, period), "PRETTY_GOOD_OSCILLATOR")


def calculate_stochastic_momentum_index(
    df: pd.DataFrame,
    period: int = 14,
    smooth_period: int = 3,
    signal_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Calculate double-smoothed Stochastic Momentum Index and signal."""
    period = positive_int(period, "period")
    smooth_period = positive_int(smooth_period, "smooth_period")
    signal_period = positive_int(signal_period, "signal_period")
    require_columns(df, ["high", "low", "close"])
    highest = df["high"].rolling(period).max()
    lowest = df["low"].rolling(period).min()
    distance = df["close"] - (highest + lowest) / 2.0
    half_range = (highest - lowest) / 2.0
    smooth_distance = _ema(_ema(distance, smooth_period), smooth_period)
    smooth_range = _ema(_ema(half_range, smooth_period), smooth_period)
    smi = 100.0 * smooth_distance / smooth_range
    return _clean(smi, "STOCHASTIC_MOMENTUM"), _clean(_ema(smi, signal_period), "STOCHASTIC_MOMENTUM_SIGNAL")


def calculate_psychological_line(
    df: pd.DataFrame, period: int = 12, source: str = "close",
) -> pd.Series:
    """Calculate the percentage of rising closes in a rolling window."""
    period = positive_int(period, "period")
    require_source(df, source)
    rising = df[source].diff().gt(0).astype(float).where(df[source].diff().notna())
    return _clean(100.0 * rising.rolling(period).mean(), "PSYCHOLOGICAL_LINE")


def calculate_rainbow_oscillator(
    df: pd.DataFrame, period: int = 2, layers: int = 10, source: str = "close",
) -> pd.Series:
    """Calculate price displacement from a layered causal SMA rainbow."""
    period = positive_int(period, "period")
    layers = positive_int(layers, "layers")
    require_source(df, source)
    layer_values = []
    current = df[source]
    for _ in range(layers):
        current = current.rolling(period).mean()
        layer_values.append(current)
    rainbow = pd.concat(layer_values, axis=1)
    mean = rainbow.mean(axis=1)
    spread = rainbow.max(axis=1) - rainbow.min(axis=1)
    return _clean(100.0 * (df[source] - mean) / spread, "RAINBOW_OSCILLATOR")
