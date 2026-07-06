def calculate_chaikin_volatility(df, ema_period=10, roc_period=10):
    high_low_range = df["high"] - df["low"]

    ema_range = high_low_range.ewm(
        span=ema_period,
        adjust=False
    ).mean()

    chaikin_volatility = (
        (ema_range - ema_range.shift(roc_period))
        / ema_range.shift(roc_period)
    ) * 100

    return chaikin_volatility