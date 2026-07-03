from indicators.ema import calculate_ema
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from indicators.bollinger import calculate_bollinger
from indicators.atr import calculate_atr
from indicators.adx import calculate_adx
from indicators.volume import calculate_volume_sma
from indicators.support_resistance import calculate_support_resistance
from indicators.candlestick import detect_candle_pattern


def calculate_indicators(df):
    # EMA
    df["EMA20"] = calculate_ema(df, 20)
    df["EMA50"] = calculate_ema(df, 50)
    df["EMA200"] = calculate_ema(df, 200)

    # RSI
    df["RSI14"] = calculate_rsi(df, 14)

    # MACD
    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)

    # Bollinger Bands
    df["BB_UPPER"], df["BB_MIDDLE"], df["BB_LOWER"] = calculate_bollinger(df)

    #ATR
    df["ATR14"] = calculate_atr(df)

    #ADX
    df["ADX14"] = calculate_adx(df)

    #VOLUME
    df["VOL_SMA20"] = calculate_volume_sma(df)

    #SUPPORT AND RESISTANCE
    df["SUPPORT"], df["RESISTANCE"] = calculate_support_resistance(df)

    #CANDLE PATTERN
    df["CANDLE_PATTERN"] = detect_candle_pattern(df)

    return df