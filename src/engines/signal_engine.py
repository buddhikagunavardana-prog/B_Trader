def generate_signals(df, strategy):
    ema = strategy.indicators["ema"]
    rsi = strategy.indicators["rsi"]

    ema_fast_col = f"EMA{ema['fast']}"
    ema_slow_col = f"EMA{ema['slow']}"
    ema_trend_col = f"EMA{ema['trend']}"
    rsi_col = f"RSI{rsi['period']}"

    df["SIGNAL"] = "HOLD"

    buy_condition = (
        (df[ema_fast_col] > df[ema_slow_col]) &
        (df["close"] > df[ema_trend_col]) &
        (df[rsi_col] > rsi["buy"]) &
        (df["MACD"] > df["MACD_SIGNAL"])
    )

    df.loc[buy_condition, "SIGNAL"] = "BUY"

    return df