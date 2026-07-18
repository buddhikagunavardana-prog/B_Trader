import numpy as np
import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate the Commodity Channel Index."""
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    typical_price = (df["high"] + df["low"] + df["close"]) / 3

    sma_tp = typical_price.rolling(window=period).mean()

    mean_deviation = typical_price.rolling(window=period).apply(
        lambda values: np.abs(values - values.mean()).mean(),
        raw=True,
    )

    cci = (typical_price - sma_tp) / (0.015 * mean_deviation)

    return cci.rename("CCI")
