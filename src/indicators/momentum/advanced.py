import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns, require_source
from src.indicators.momentum.rsi import calculate_rsi


def _clean(series: pd.Series, name: str) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).rename(name)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_trix(
    df: pd.DataFrame, period: int = 15, source: str = "close",
) -> pd.Series:
    """Calculate the rate of change of a triple-smoothed EMA."""
    period = positive_int(period, "period")
    require_source(df, source)
    triple = _ema(_ema(_ema(df[source], period), period), period)
    return _clean(triple.pct_change() * 100.0, "TRIX")


def calculate_ppo(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate PPO, signal, and histogram from shared EMA components."""
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    signal_period = positive_int(signal_period, "signal_period")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_source(df, source)
    fast = _ema(df[source], fast_period)
    slow = _ema(df[source], slow_period)
    ppo = 100.0 * (fast - slow) / slow
    signal = _ema(ppo, signal_period)
    return (
        _clean(ppo, "PPO"),
        _clean(signal, "PPO_SIGNAL"),
        _clean(ppo - signal, "PPO_HISTOGRAM"),
    )


def calculate_apo(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    source: str = "close",
) -> pd.Series:
    """Calculate the Absolute Price Oscillator."""
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_source(df, source)
    return _clean(_ema(df[source], fast_period) - _ema(df[source], slow_period), "APO")


def calculate_cmo(
    df: pd.DataFrame, period: int = 14, source: str = "close",
) -> pd.Series:
    """Calculate the Chande Momentum Oscillator."""
    period = positive_int(period, "period")
    require_source(df, source)
    delta = df[source].diff()
    gains = delta.clip(lower=0).rolling(period).sum()
    losses = (-delta.clip(upper=0)).rolling(period).sum()
    return _clean(100.0 * (gains - losses) / (gains + losses), "CMO")


def calculate_connors_rsi(
    df: pd.DataFrame,
    rsi_period: int = 3,
    streak_period: int = 2,
    rank_period: int = 100,
    source: str = "close",
) -> pd.Series:
    """Calculate Connors RSI from price RSI, streak RSI, and ROC rank."""
    rsi_period = positive_int(rsi_period, "rsi_period")
    streak_period = positive_int(streak_period, "streak_period")
    rank_period = positive_int(rank_period, "rank_period")
    require_source(df, source)
    price_frame = pd.DataFrame({"close": df[source]}, index=df.index)
    price_rsi = calculate_rsi(price_frame, rsi_period)
    direction = np.sign(df[source].diff()).fillna(0.0).to_numpy()
    streak = np.zeros(len(df), dtype=float)
    for index in range(1, len(df)):
        if direction[index] == 0:
            streak[index] = 0
        elif direction[index] == direction[index - 1]:
            streak[index] = streak[index - 1] + direction[index]
        else:
            streak[index] = direction[index]
    streak_frame = pd.DataFrame({"close": streak}, index=df.index)
    streak_rsi = calculate_rsi(streak_frame, streak_period)
    one_period_roc = df[source].pct_change() * 100.0
    rank = one_period_roc.rolling(rank_period).apply(
        lambda values: 100.0 * np.mean(values[:-1] < values[-1]), raw=True,
    )
    return _clean((price_rsi + streak_rsi + rank) / 3.0, "CONNORS_RSI")


def calculate_rmi(
    df: pd.DataFrame,
    period: int = 14,
    momentum_period: int = 5,
    source: str = "close",
) -> pd.Series:
    """Calculate the Relative Momentum Index."""
    period = positive_int(period, "period")
    momentum_period = positive_int(momentum_period, "momentum_period")
    require_source(df, source)
    momentum = df[source].diff(momentum_period)
    gains = momentum.clip(lower=0).rolling(period).mean()
    losses = (-momentum.clip(upper=0)).rolling(period).mean()
    return _clean(100.0 * gains / (gains + losses), "RMI")


def calculate_fisher_transform(
    df: pd.DataFrame, period: int = 10,
) -> pd.Series:
    """Calculate a causal Fisher Transform of median price."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    median = (df["high"] + df["low"]) / 2.0
    lowest = median.rolling(period).min()
    highest = median.rolling(period).max()
    raw = (2.0 * ((median - lowest) / (highest - lowest) - 0.5)).clip(-0.999, 0.999)
    smooth = np.full(len(df), np.nan)
    fisher = np.full(len(df), np.nan)
    raw_values = raw.to_numpy(copy=False)
    for index in range(period - 1, len(df)):
        if not np.isfinite(raw_values[index]):
            continue
        previous = smooth[index - 1] if index and np.isfinite(smooth[index - 1]) else 0.0
        smooth[index] = np.clip(0.33 * raw_values[index] + 0.67 * previous, -0.999, 0.999)
        fisher[index] = 0.5 * np.log((1 + smooth[index]) / (1 - smooth[index]))
    return pd.Series(fisher, index=df.index, name="FISHER_TRANSFORM")


def calculate_awesome_oscillator(
    df: pd.DataFrame, fast_period: int = 5, slow_period: int = 34,
) -> pd.Series:
    """Calculate the Awesome Oscillator from median price SMAs."""
    fast_period = positive_int(fast_period, "fast_period")
    slow_period = positive_int(slow_period, "slow_period")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    require_columns(df, ["high", "low"])
    median = (df["high"] + df["low"]) / 2.0
    return _clean(
        median.rolling(fast_period).mean() - median.rolling(slow_period).mean(),
        "AWESOME_OSCILLATOR",
    )


def calculate_balance_of_power(df: pd.DataFrame) -> pd.Series:
    """Calculate Balance of Power from candle body and range."""
    require_columns(df, ["open", "high", "low", "close"])
    return _clean((df["close"] - df["open"]) / (df["high"] - df["low"]), "BALANCE_OF_POWER")


def calculate_coppock_curve(
    df: pd.DataFrame,
    short_period: int = 11,
    long_period: int = 14,
    wma_period: int = 10,
    source: str = "close",
) -> pd.Series:
    """Calculate the Coppock Curve from two ROCs and a WMA."""
    short_period = positive_int(short_period, "short_period")
    long_period = positive_int(long_period, "long_period")
    wma_period = positive_int(wma_period, "wma_period")
    require_source(df, source)
    combined = df[source].pct_change(short_period) * 100.0 + df[source].pct_change(long_period) * 100.0
    weights = np.arange(1, wma_period + 1, dtype=float)
    result = combined.rolling(wma_period).apply(
        lambda values: float(np.dot(values, weights) / weights.sum()), raw=True,
    )
    return _clean(result, "COPPOCK_CURVE")
