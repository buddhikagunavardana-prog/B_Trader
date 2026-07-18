import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_directional_movement(
    df: pd.DataFrame, period: int = 14,
) -> tuple[pd.Series, pd.Series]:
    """Return shared causal positive and negative directional indicators."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    upward = df["high"].diff()
    downward = -df["low"].diff()
    plus_dm = upward.where((upward > downward) & (upward > 0), 0.0)
    minus_dm = downward.where((downward > upward) & (downward > 0), 0.0)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(period).mean()
    plus = 100.0 * plus_dm.rolling(period).mean() / atr
    minus = 100.0 * minus_dm.rolling(period).mean() / atr
    return (
        plus.replace([np.inf, -np.inf], np.nan).rename("PLUS_DI"),
        minus.replace([np.inf, -np.inf], np.nan).rename("MINUS_DI"),
    )


def calculate_plus_di(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the positive directional indicator."""
    return calculate_directional_movement(df, period)[0]


def calculate_minus_di(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the negative directional indicator."""
    return calculate_directional_movement(df, period)[1]
