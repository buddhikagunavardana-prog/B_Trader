import numpy as np


def calculate_wma(df, period=20, source="close"):
    """
    Calculate Weighted Moving Average (WMA).

    Parameters
    ----------
    df : pandas.DataFrame
        OHLCV dataframe.
    period : int
        WMA period.
    source : str
        Price column.

    Returns
    -------
    pandas.Series
        WMA values.
    """

    weights = np.arange(1, period + 1)

    return df[source].rolling(period).apply(
        lambda prices: np.dot(prices, weights) / weights.sum(),
        raw=True
    )