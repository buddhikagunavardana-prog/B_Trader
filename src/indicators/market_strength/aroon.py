import numpy as np


def calculate_aroon(df, period=25):
    aroon_up = df["high"].rolling(period + 1).apply(
        lambda x: 100 * (period - (period - np.argmax(x))) / period,
        raw=True
    )

    aroon_down = df["low"].rolling(period + 1).apply(
        lambda x: 100 * (period - (period - np.argmin(x))) / period,
        raw=True
    )

    return aroon_up, aroon_down