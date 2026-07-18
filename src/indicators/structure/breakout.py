import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_breakout_levels(
    df: pd.DataFrame, period: int = 20,
) -> tuple[pd.Series, pd.Series]:
    """Return current rolling breakout extrema for backward compatibility."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    breakout_high = df["high"].rolling(window=period).max()
    breakout_low = df["low"].rolling(window=period).min()
    return breakout_high, breakout_low


def calculate_breakout_detection(
    df: pd.DataFrame, period: int = 20,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Detect closes beyond prior rolling extrema without look-ahead."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    upper = df["high"].rolling(period).max().shift(1).rename("BREAKOUT_UPPER")
    lower = df["low"].rolling(period).min().shift(1).rename("BREAKOUT_LOWER")
    bullish = df["close"].gt(upper).astype(float).where(upper.notna()).rename("BREAKOUT_BULLISH")
    bearish = df["close"].lt(lower).astype(float).where(lower.notna()).rename("BREAKOUT_BEARISH")
    return upper, lower, bullish, bearish
