import pandas as pd

from src.indicators._validation import positive_int, require_source


def calculate_zscore(
    df: pd.DataFrame,
    period: int = 20,
    source: str = "close",
) -> pd.Series:
    period = positive_int(period, "period")
    require_source(df, source)
    mean = df[source].rolling(period).mean()
    deviation = df[source].rolling(period).std()
    return ((df[source] - mean) / deviation).rename("ZSCORE")
