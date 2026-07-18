import numpy as np
import pandas as pd

from src.indicators._validation import require_columns


def calculate_adl(df: pd.DataFrame) -> pd.Series:
    """Calculate the Accumulation/Distribution Line."""
    require_columns(df, ["high", "low", "close", "volume"])
    candle_range = (df["high"] - df["low"]).replace(0, np.nan)
    money_flow_multiplier = (
        ((df["close"] - df["low"]) - (df["high"] - df["close"]))
        / candle_range
    )
    money_flow_volume = money_flow_multiplier.fillna(0.0) * df["volume"]
    return money_flow_volume.cumsum().rename("ACCUMULATION_DISTRIBUTION")
