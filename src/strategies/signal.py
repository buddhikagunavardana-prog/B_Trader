def generate_signal(ema20, ema50, rsi, macd, macd_signal):

    score = 0

    if ema20 > ema50:
        score += 1
    else:
        score -= 1

    if rsi > 55:
        score += 1
    elif rsi < 45:
        score -= 1

    if macd > macd_signal:
        score += 1
    else:
        score -= 1

    if score >= 2:
        return "BUY"

    elif score <= -2:
        return "SELL"

    return "HOLD"