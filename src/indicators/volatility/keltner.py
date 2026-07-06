from src.indicators.trend.ema import calculate_ema
from src.indicators.volatility.atr import calculate_atr


def calculate_keltner_channel(df, ema_period=20, atr_period=10, multiplier=2):
    middle = calculate_ema(df, period=ema_period)
    atr = calculate_atr(df, period=atr_period)

    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)

    return upper, middle, lower