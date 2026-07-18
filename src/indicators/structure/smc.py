import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_fair_value_gap(
    df: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Confirm three-candle fair-value gaps on the third candle.

    This experimental rule emits an event only when candle t confirms a gap
    versus candle t-2. Bounds are reported at confirmation time; gaps are not
    persisted, and later invalidation is therefore outside this event output.
    """
    require_columns(df, ["high", "low"])
    bullish = df["low"].gt(df["high"].shift(2))
    bearish = df["high"].lt(df["low"].shift(2))
    ready = df["high"].shift(2).notna() & df["low"].shift(2).notna()
    lower = pd.Series(np.nan, index=df.index, name="FVG_LOWER")
    upper = pd.Series(np.nan, index=df.index, name="FVG_UPPER")
    lower.loc[bullish] = df["high"].shift(2).loc[bullish]
    upper.loc[bullish] = df["low"].loc[bullish]
    lower.loc[bearish] = df["high"].loc[bearish]
    upper.loc[bearish] = df["low"].shift(2).loc[bearish]
    return (
        bullish.astype(float).where(ready).rename("FVG_BULLISH"),
        bearish.astype(float).where(ready).rename("FVG_BEARISH"),
        lower,
        upper,
    )


def calculate_order_block(
    df: pd.DataFrame, period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Approximate order blocks after a confirmed prior-range breakout.

    The previous opposite candle supplies the block bounds. Confirmation and
    output occur on the breakout candle, so there is a one-candle delay from
    the candidate block. Outputs are event-only; later close through a bound
    is the invalidation rule for downstream state tracking. Experimental.
    """
    period = positive_int(period, "period")
    require_columns(df, ["open", "high", "low", "close"])
    prior_high = df["high"].rolling(period).max().shift(1)
    prior_low = df["low"].rolling(period).min().shift(1)
    previous_bearish = df["close"].shift(1).lt(df["open"].shift(1))
    previous_bullish = df["close"].shift(1).gt(df["open"].shift(1))
    bullish = df["close"].gt(prior_high) & previous_bearish
    bearish = df["close"].lt(prior_low) & previous_bullish
    ready = prior_high.notna() & prior_low.notna()
    lower = pd.Series(np.nan, index=df.index, name="ORDER_BLOCK_LOWER")
    upper = pd.Series(np.nan, index=df.index, name="ORDER_BLOCK_UPPER")
    active = bullish | bearish
    lower.loc[active] = df["low"].shift(1).loc[active]
    upper.loc[active] = df["high"].shift(1).loc[active]
    return (
        bullish.astype(float).where(ready).rename("ORDER_BLOCK_BULLISH"),
        bearish.astype(float).where(ready).rename("ORDER_BLOCK_BEARISH"),
        lower,
        upper,
    )


def calculate_market_structure(
    df: pd.DataFrame, period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Approximate causal BOS and CHoCH from prior-range close breaks.

    A close beyond the preceding rolling extreme confirms immediately. A break
    in the active trend is BOS; an opposite break is CHoCH and flips trend.
    The rule is experimental, event-based, and has no future-candle delay.
    """
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    prior_high = df["high"].rolling(period).max().shift(1)
    prior_low = df["low"].rolling(period).min().shift(1)
    upward = df["close"].gt(prior_high).to_numpy()
    downward = df["close"].lt(prior_low).to_numpy()
    ready = (prior_high.notna() & prior_low.notna()).to_numpy()
    bos = np.full(len(df), np.nan)
    choch = np.full(len(df), np.nan)
    trend = np.full(len(df), np.nan)
    state = 0.0
    for index in range(len(df)):
        if not ready[index]:
            continue
        bos[index] = 0.0
        choch[index] = 0.0
        if upward[index]:
            if state < 0:
                choch[index] = 1.0
            else:
                bos[index] = 1.0
            state = 1.0
        elif downward[index]:
            if state > 0:
                choch[index] = -1.0
            else:
                bos[index] = -1.0
            state = -1.0
        trend[index] = state
    return (
        pd.Series(bos, index=df.index, name="BOS"),
        pd.Series(choch, index=df.index, name="CHOCH"),
        pd.Series(trend, index=df.index, name="MARKET_STRUCTURE_TREND"),
    )
