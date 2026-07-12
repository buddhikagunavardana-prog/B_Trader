import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_fibonacci_retracement(
    df: pd.DataFrame,
    period: int = 20,
) -> dict[str, pd.Series]:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low"])
    high = df["high"].rolling(period).max()
    low = df["low"].rolling(period).min()
    difference = high - low
    return {
        "0.0": high,
        "23.6": high - difference * 0.236,
        "38.2": high - difference * 0.382,
        "50.0": high - difference * 0.500,
        "61.8": high - difference * 0.618,
        "78.6": high - difference * 0.786,
        "100.0": low,
    }
