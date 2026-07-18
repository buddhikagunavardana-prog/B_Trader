import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns
from src.indicators.structure.smc import calculate_fair_value_gap, calculate_market_structure, calculate_order_block
from src.indicators.structure.swing import calculate_swing_points


def calculate_inverse_fair_value_gap(
    df: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Emit an experimental inverse-FVG event when a confirmed gap is closed through."""
    require_columns(df, ["high", "low", "close"])
    fvg_bull, fvg_bear, fvg_lower, fvg_upper = calculate_fair_value_gap(df)
    fvg_bull_values = fvg_bull.to_numpy(copy=False)
    fvg_bear_values = fvg_bear.to_numpy(copy=False)
    fvg_lower_values = fvg_lower.to_numpy(copy=False)
    fvg_upper_values = fvg_upper.to_numpy(copy=False)
    closes = df["close"].to_numpy(copy=False)
    bullish = np.full(len(df), np.nan)
    bearish = np.full(len(df), np.nan)
    lower = np.full(len(df), np.nan)
    upper = np.full(len(df), np.nan)
    active_bull = active_bear = None
    for index in range(len(df)):
        if index >= 2:
            bullish[index] = bearish[index] = 0.0
        if fvg_bull_values[index] == 1.0:
            active_bull = (fvg_lower_values[index], fvg_upper_values[index])
        if fvg_bear_values[index] == 1.0:
            active_bear = (fvg_lower_values[index], fvg_upper_values[index])
        close = closes[index]
        if active_bear is not None and close > active_bear[1]:
            bullish[index], lower[index], upper[index] = 1.0, active_bear[0], active_bear[1]
            active_bear = None
        if active_bull is not None and close < active_bull[0]:
            bearish[index], lower[index], upper[index] = 1.0, active_bull[0], active_bull[1]
            active_bull = None
    return (
        pd.Series(bullish, index=df.index, name="INVERSE_FVG_BULLISH"),
        pd.Series(bearish, index=df.index, name="INVERSE_FVG_BEARISH"),
        pd.Series(lower, index=df.index, name="INVERSE_FVG_LOWER"),
        pd.Series(upper, index=df.index, name="INVERSE_FVG_UPPER"),
    )


def calculate_liquidity_sweep(
    df: pd.DataFrame, period: int = 5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Flag experimental wick sweeps of the latest confirmed swing level."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    swing_high, swing_low = calculate_swing_points(df, period)
    high_level = df["high"].shift(period).where(swing_high).ffill().shift(1)
    low_level = df["low"].shift(period).where(swing_low).ffill().shift(1)
    high_condition = df["high"].gt(high_level) & df["close"].lt(high_level)
    low_condition = df["low"].lt(low_level) & df["close"].gt(low_level)
    high_event = high_condition & ~high_condition.shift(1, fill_value=False)
    low_event = low_condition & ~low_condition.shift(1, fill_value=False)
    ready = high_level.notna() | low_level.notna()
    level = high_level.where(high_event).combine_first(low_level.where(low_event))
    return (
        high_event.astype(float).where(ready).rename("LIQUIDITY_SWEEP_HIGH"),
        low_event.astype(float).where(ready).rename("LIQUIDITY_SWEEP_LOW"),
        level.rename("LIQUIDITY_SWEEP_LEVEL"),
    )


def calculate_equal_highs(
    df: pd.DataFrame, period: int = 5, tolerance: float = 0.001,
) -> tuple[pd.Series, pd.Series]:
    """Confirm experimental equal swing highs after the right-side swing delay."""
    period = positive_int(period, "period")
    tolerance = positive_float(tolerance, "tolerance")
    require_columns(df, ["high", "low"])
    swing_high, _ = calculate_swing_points(df, period)
    level = df["high"].shift(period).where(swing_high)
    previous = level.ffill().shift(1)
    event = level.notna() & previous.notna() & ((level - previous).abs() / previous.abs()).le(tolerance)
    ready = df["high"].rolling(2 * period + 1).count().eq(2 * period + 1)
    return event.astype(float).where(ready).rename("EQUAL_HIGHS"), level.where(event).rename("EQUAL_HIGH_LEVEL")


def calculate_equal_lows(
    df: pd.DataFrame, period: int = 5, tolerance: float = 0.001,
) -> tuple[pd.Series, pd.Series]:
    """Confirm experimental equal swing lows after the right-side swing delay."""
    period = positive_int(period, "period")
    tolerance = positive_float(tolerance, "tolerance")
    require_columns(df, ["high", "low"])
    _, swing_low = calculate_swing_points(df, period)
    level = df["low"].shift(period).where(swing_low)
    previous = level.ffill().shift(1)
    event = level.notna() & previous.notna() & ((level - previous).abs() / previous.abs()).le(tolerance)
    ready = df["low"].rolling(2 * period + 1).count().eq(2 * period + 1)
    return event.astype(float).where(ready).rename("EQUAL_LOWS"), level.where(event).rename("EQUAL_LOW_LEVEL")


def calculate_breaker_block(
    df: pd.DataFrame, period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Emit an experimental breaker event when a prior order block is invalidated."""
    period = positive_int(period, "period")
    require_columns(df, ["open", "high", "low", "close"])
    ob_bull, ob_bear, ob_lower, ob_upper = calculate_order_block(df, period)
    bos, choch, _ = calculate_market_structure(df, period)
    ob_bull_values = ob_bull.to_numpy(copy=False)
    ob_bear_values = ob_bear.to_numpy(copy=False)
    ob_lower_values = ob_lower.to_numpy(copy=False)
    ob_upper_values = ob_upper.to_numpy(copy=False)
    bos_values = bos.to_numpy(copy=False)
    choch_values = choch.to_numpy(copy=False)
    closes = df["close"].to_numpy(copy=False)
    bullish = np.full(len(df), np.nan)
    bearish = np.full(len(df), np.nan)
    lower = np.full(len(df), np.nan)
    upper = np.full(len(df), np.nan)
    active_bull = active_bear = None
    for index in range(len(df)):
        if index >= period:
            bullish[index] = bearish[index] = 0.0
        if ob_bull_values[index] == 1.0:
            active_bull = (ob_lower_values[index], ob_upper_values[index])
        if ob_bear_values[index] == 1.0:
            active_bear = (ob_lower_values[index], ob_upper_values[index])
        upward_structure = bos_values[index] == 1.0 or choch_values[index] == 1.0
        downward_structure = bos_values[index] == -1.0 or choch_values[index] == -1.0
        close = closes[index]
        if active_bear is not None and close > active_bear[1] and upward_structure:
            bullish[index], lower[index], upper[index] = 1.0, active_bear[0], active_bear[1]
            active_bear = None
        if active_bull is not None and close < active_bull[0] and downward_structure:
            bearish[index], lower[index], upper[index] = 1.0, active_bull[0], active_bull[1]
            active_bull = None
    return (
        pd.Series(bullish, index=df.index, name="BREAKER_BLOCK_BULLISH"),
        pd.Series(bearish, index=df.index, name="BREAKER_BLOCK_BEARISH"),
        pd.Series(lower, index=df.index, name="BREAKER_BLOCK_LOWER"),
        pd.Series(upper, index=df.index, name="BREAKER_BLOCK_UPPER"),
    )
