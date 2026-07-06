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
    medium_body = body <= candle_range * 0.3

    long_lower_shadow = lower_shadow >= body * 2
    long_upper_shadow = upper_shadow >= body * 2

    prev_open = open_price.shift(1)
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    prev_body = body.shift(1)
    prev_range = candle_range.shift(1)

    prev_bullish = prev_close > prev_open
    prev_bearish = prev_close < prev_open

    open_2 = open_price.shift(2)
    close_2 = close.shift(2)
    high_2 = high.shift(2)
    low_2 = low.shift(2)

    candle_2_bullish = close_2 > open_2
    candle_2_bearish = close_2 < open_2
    candle_1_small = prev_body <= prev_range * 0.3

    # 1. Doji
    result["doji"] = small_body

    # 2. Dragonfly Doji
    result["dragonfly_doji"] = (
        small_body
        & (upper_shadow <= candle_range * 0.1)
        & (lower_shadow >= candle_range * 0.6)
    )

    # 3. Gravestone Doji
    result["gravestone_doji"] = (
        small_body
        & (lower_shadow <= candle_range * 0.1)
        & (upper_shadow >= candle_range * 0.6)
    )

    # 4. Hammer
    result["hammer"] = (
        bullish
        & long_lower_shadow
        & (upper_shadow <= body)
    )

    # 5. Hanging Man
    result["hanging_man"] = (
        bearish
        & long_lower_shadow
        & (upper_shadow <= body)
    )

    # 6. Inverted Hammer
    result["inverted_hammer"] = (
        bullish
        & long_upper_shadow
        & (lower_shadow <= body)
    )

    # 7. Shooting Star
    result["shooting_star"] = (
        bearish
        & long_upper_shadow
        & (lower_shadow <= body)
    )

    # 8. Bullish Engulfing
    result["bullish_engulfing"] = (
        prev_bearish
        & bullish
        & (open_price < prev_close)
        & (close > prev_open)
    )

    # 9. Bearish Engulfing
    result["bearish_engulfing"] = (
        prev_bullish
        & bearish
        & (open_price > prev_close)
        & (close < prev_open)
    )

    # 10. Bullish Harami
    result["bullish_harami"] = (
        prev_bearish
        & bullish
        & (open_price > prev_close)
        & (close < prev_open)
    )

    # 11. Bearish Harami
    result["bearish_harami"] = (
        prev_bullish
        & bearish
        & (open_price < prev_close)
        & (close > prev_open)
    )

    # 12. Morning Star
    result["morning_star"] = (
        candle_2_bearish
        & candle_1_small
        & bullish
        & (close > ((open_2 + close_2) / 2))
    )

    # 13. Evening Star
    result["evening_star"] = (
        candle_2_bullish
        & candle_1_small
        & bearish
        & (close < ((open_2 + close_2) / 2))
    )

    # 14. Bullish Marubozu
    result["bullish_marubozu"] = (
        bullish
        & (upper_shadow <= body * 0.1)
        & (lower_shadow <= body * 0.1)
    )

    # 15. Bearish Marubozu
    result["bearish_marubozu"] = (
        bearish
        & (upper_shadow <= body * 0.1)
        & (lower_shadow <= body * 0.1)
    )

    # 16. Spinning Top
    result["spinning_top"] = (
        medium_body
        & (upper_shadow >= body)
        & (lower_shadow >= body)
    )

    # 17. Tweezer Bottom
    result["tweezer_bottom"] = (
        prev_bearish
        & bullish
        & ((low - prev_low).abs() <= candle_range * 0.1)
    )

    # 18. Tweezer Top
    result["tweezer_top"] = (
        prev_bullish
        & bearish
        & ((high - prev_high).abs() <= candle_range * 0.1)
    )

    # 19. Piercing Line
    result["piercing_line"] = (
        prev_bearish
        & bullish
        & (open_price < prev_low)
        & (close > ((prev_open + prev_close) / 2))
        & (close < prev_open)
    )

    # 20. Dark Cloud Cover
    result["dark_cloud_cover"] = (
        prev_bullish
        & bearish
        & (open_price > prev_high)
        & (close < ((prev_open + prev_close) / 2))
        & (close > prev_open)
    )

    # 21. Three White Soldiers
    result["three_white_soldiers"] = (
        bullish
        & bullish.shift(1)
        & bullish.shift(2)
        & (close > prev_close)
        & (prev_close > close_2)
    )

    # 22. Three Black Crows
    result["three_black_crows"] = (
        bearish
        & bearish.shift(1)
        & bearish.shift(2)
        & (close < prev_close)
        & (prev_close < close_2)
    )

    # 23. Inside Bar
    result["inside_bar"] = (
        (high < prev_high)
        & (low > prev_low)
    )

    # 24. Outside Bar
    result["outside_bar"] = (
        (high > prev_high)
        & (low < prev_low)
    )

    # 25. Gap Up
    result["gap_up"] = low > prev_high

    # 26. Gap Down
    result["gap_down"] = high < prev_low

    return result


def detect_candle_pattern(df):
    patterns = calculate_candlestick_patterns(df)

    result = pd.Series("NONE", index=df.index)

    priority = [
        "morning_star",
        "evening_star",
        "three_white_soldiers",
        "three_black_crows",
        "bullish_engulfing",
        "bearish_engulfing",
        "piercing_line",
        "dark_cloud_cover",
        "tweezer_bottom",
        "tweezer_top",
        "hammer",
        "shooting_star",
        "inverted_hammer",
        "hanging_man",
        "bullish_harami",
        "bearish_harami",
        "bullish_marubozu",
        "bearish_marubozu",
        "dragonfly_doji",
        "gravestone_doji",
        "spinning_top",
        "inside_bar",
        "outside_bar",
        "gap_up",
        "gap_down",
        "doji",
    ]

    for pattern in priority:
        result = result.mask(patterns[pattern], pattern.upper())

    return result