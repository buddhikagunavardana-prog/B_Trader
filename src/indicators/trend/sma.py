import pandas as pd


def calculate_sma(df, period=20, source="close"):
    """
    Calculate Simple Moving Average (SMA).

    Parameters
    ----------
    df : pandas.DataFrame
        OHLCV dataframe.
    period : int
        SMA period.
    source : str
        Price column.

    Returns
    -------
    pandas.Series
        SMA values.
    """

    return df[source].rolling(window=period).mean()