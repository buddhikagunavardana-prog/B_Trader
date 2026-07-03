import pandas as pd


def calculate_bollinger(df, period=20, std_dev=2):
    sma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    return upper, sma, lower