import numpy as np
import pandas as pd

from src.indicators._validation import require_columns


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """Calculate vectorized On-Balance Volume from close direction."""
    require_columns(df, ["close", "volume"])
    direction = np.sign(df["close"].diff()).fillna(0.0)
    return (direction * df["volume"]).cumsum().rename("OBV")
