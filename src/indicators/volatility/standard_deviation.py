import pandas as pd

from src.indicators._validation import positive_int, require_source


def calculate_standard_deviation(
    df: pd.DataFrame,
    period: int = 20,
    source: str = "close",
) -> pd.Series:
    period = positive_int(period, "period")
    require_source(df, source)
    return df[source].rolling(period).std().rename("STANDARD_DEVIATION")
