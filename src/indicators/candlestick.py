def detect_candle_pattern(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    body = abs(last["close"] - last["open"])
    candle_range = last["high"] - last["low"]

    if candle_range == 0:
        return "NONE"

    upper_wick = last["high"] - max(last["close"], last["open"])
    lower_wick = min(last["close"], last["open"]) - last["low"]

    if lower_wick > body * 2 and upper_wick < body:
        return "HAMMER"

    if upper_wick > body * 2 and lower_wick < body:
        return "SHOOTING_STAR"

    if last["close"] > last["open"] and prev["close"] < prev["open"]:
        if last["close"] > prev["open"] and last["open"] < prev["close"]:
            return "BULLISH_ENGULFING"

    if last["close"] < last["open"] and prev["close"] > prev["open"]:
        if last["open"] > prev["close"] and last["close"] < prev["open"]:
            return "BEARISH_ENGULFING"

    return "NONE"