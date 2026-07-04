from indicators.ema import calculate_ema
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from indicators.bollinger import calculate_bollinger
from indicators.atr import calculate_atr
from indicators.adx import calculate_adx
from indicators.volume import calculate_volume_sma
from indicators.support_resistance import calculate_support_resistance
from indicators.candlestick import detect_candle_pattern


def calculate_indicators(df, strategy):

    indicators = strategy.indicators

    # =====================
    # EMA
    # =====================

    ema = indicators.get("ema", {})

    if ema.get("enabled", False):

        fast = ema.get("fast", 20)
        slow = ema.get("slow", 50)
        trend = ema.get("trend", 200)

        df[f"EMA{fast}"] = calculate_ema(df, fast)
        df[f"EMA{slow}"] = calculate_ema(df, slow)
        df[f"EMA{trend}"] = calculate_ema(df, trend)

    # =====================
    # RSI
    # =====================

    rsi = indicators.get("rsi", {})

    if rsi.get("enabled", False):

        period = rsi.get("period", 14)

        df[f"RSI{period}"] = calculate_rsi(df, period)

    # =====================
    # MACD
    # =====================

    macd = indicators.get("macd", {})

    if macd.get("enabled", False):

        df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(
            df,
            macd.get("fast", 12),
            macd.get("slow", 26),
            macd.get("signal", 9),
        )

    # =====================
    # ATR
    # =====================

    atr = indicators.get("atr", {})

    if atr.get("enabled", False):

        period = atr.get("period", 14)

        df[f"ATR{period}"] = calculate_atr(df, period)

    # =====================
    # Other Indicators
    # =====================

    df["BB_UPPER"], df["BB_MIDDLE"], df["BB_LOWER"] = calculate_bollinger(df)

    df["ADX14"] = calculate_adx(df)

    df["VOL_SMA20"] = calculate_volume_sma(df)

    df["SUPPORT"], df["RESISTANCE"] = calculate_support_resistance(df)

    df["CANDLE_PATTERN"] = detect_candle_pattern(df)

    return df