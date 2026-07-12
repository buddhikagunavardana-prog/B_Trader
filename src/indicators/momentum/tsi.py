import pandas as pd

from src.indicators._validation import positive_int, require_source


def calculate_tsi(
    df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    source: str = "close",
) -> pd.Series:
    long_period = positive_int(long_period, "long_period")
    short_period = positive_int(short_period, "short_period")
    require_source(df, source)
    momentum = df[source].diff()
    numerator = momentum.ewm(span=long_period, adjust=False).mean().ewm(
        span=short_period, adjust=False,
    ).mean()
    denominator = momentum.abs().ewm(span=long_period, adjust=False).mean().ewm(
        span=short_period, adjust=False,
    ).mean()
    return (100.0 * numerator / denominator).rename("TSI")
