import numpy as np

from src.indicators.trend.wma import calculate_wma


def calculate_hma(df, period=20, source="close"):
    """
    Calculate Hull Moving Average (HMA).

    Parameters
    ----------
    df : pandas.DataFrame
        OHLCV dataframe.
    period : int
        HMA period.
    source : str
        Price column.

    Returns
    -------
    pandas.Series
        HMA values.
    """

    half_period = max(int(period / 2), 1)
    sqrt_period = max(int(np.sqrt(period)), 1)

    wma_half = calculate_wma(df, period=half_period, source=source)
    wma_full = calculate_wma(df, period=period, source=source)

    temp = 2 * wma_half - wma_full

    temp_df = df.copy()
    temp_df[source] = temp

    hma = calculate_wma(
        temp_df,
        period=sqrt_period,
        source=source
    )

    return hma