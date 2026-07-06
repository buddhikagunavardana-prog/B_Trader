import pandas as pd


def calculate_candlestick_patterns(df):
    result = pd.DataFrame(index=df.index)

    open_price = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    body = (close - open_price).abs()
    candle_range = high - low

    upper_shadow = high - pd.concat([open_price, close], axis=1).max(axis=1)
    lower_shadow = pd.concat([open_price, close], axis=1).min(axis=1) - low

    bullish = close > open_price
    bearish = close < open_price

    small_body = body <= candle_range * 0.1
    long_lower_shadow = lower_shadow >= body * 2
    long_upper_shadow = upper_shadow >= body * 2

    result["doji"] = small_body

    result["hammer"] = (
        long_lower_shadow
        & (upper_shadow <= body)
        & bullish
    )

    result["inverted_hammer"] = (
        long_upper_shadow
        & (lower_shadow <= body)
        & bullish
    )

    result["hanging_man"] = (
        long_lower_shadow
        & (upper_shadow <= body)
        & bearish
    )

    result["shooting_star"] = (
        long_upper_shadow
        & (lower_shadow <= body)
        & bearish
    )

    prev_open = open_price.shift(1)
    prev_close = close.shift(1)

    prev_bullish = prev_close > prev_open
    prev_bearish = prev_close < prev_open

    result["bullish_engulfing"] = (
        prev_bearish
        & bullish
        & (open_price < prev_close)
        & (close > prev_open)
    )

    result["bearish_engulfing"] = (
        prev_bullish
        & bearish
        & (open_price > prev_close)
        & (close < prev_open)
    )

    result["bullish_harami"] = (
        prev_bearish
        & bullish
        & (open_price > prev_close)
        & (close < prev_open)
    )

    result["bearish_harami"] = (
        prev_bullish
        & bearish
        & (open_price < prev_close)
        & (close > prev_open)
    )

    open_2 = open_price.shift(2)
    close_2 = close.shift(2)

    candle_2_bearish = close_2 < open_2
    candle_2_bullish = close_2 > open_2

    candle_1_small = body.shift(1) <= candle_range.shift(1) * 0.3

    result["morning_star"] = (
        candle_2_bearish
        & candle_1_small
        & bullish
        & (close > ((open_2 + close_2) / 2))
    )

    result["evening_star"] = (
        candle_2_bullish
        & candle_1_small
        & bearish
        & (close < ((open_2 + close_2) / 2))
    )

    return result


def detect_candle_pattern(df):
    patterns = calculate_candlestick_patterns(df)

    result = pd.Series("NONE", index=df.index)

    priority = [
        "morning_star",
        "evening_star",
        "bullish_engulfing",
        "bearish_engulfing",
        "hammer",
        "shooting_star",
        "inverted_hammer",
        "hanging_man",
        "bullish_harami",
        "bearish_harami",
        "doji",
    ]

    for pattern in priority:
        result = result.mask(patterns[pattern], pattern.upper())

    return result