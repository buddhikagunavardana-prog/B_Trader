import pandas as pd


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
):
    ema_fast = df["close"].ewm(
        span=fast,
        adjust=False
    ).mean()

    ema_slow = df["close"].ewm(
        span=slow,
        adjust=False
    ).mean()

    macd = ema_fast - ema_slow

    signal_line = macd.ewm(
        span=signal,
        adjust=False
    ).mean()

    histogram = macd - signal_line

    return macd, signal_line, histogram