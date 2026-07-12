import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_source


def calculate_historical_volatility(
    df: pd.DataFrame,
    period: int = 20,
    annualization: float = 365.0,
    source: str = "close",
) -> pd.Series:
    period = positive_int(period, "period")
    annualization = positive_float(annualization, "annualization")
    require_source(df, source)
    log_returns = np.log(df[source] / df[source].shift())
    return (log_returns.rolling(period).std() * np.sqrt(annualization) * 100).rename(
        "HISTORICAL_VOLATILITY",
    )
