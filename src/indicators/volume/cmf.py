def calculate_cmf(df, period=20):
    money_flow_multiplier = (
        ((df["close"] - df["low"]) - (df["high"] - df["close"]))
        / (df["high"] - df["low"])
    )

    money_flow_volume = money_flow_multiplier * df["volume"]

    cmf = (
        money_flow_volume.rolling(window=period).sum()
        / df["volume"].rolling(window=period).sum()
    )

    return cmf