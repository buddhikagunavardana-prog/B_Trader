def calculate_adl(df):
    money_flow_multiplier = (
        ((df["close"] - df["low"]) - (df["high"] - df["close"]))
        / (df["high"] - df["low"])
    )

    money_flow_volume = money_flow_multiplier * df["volume"]

    adl = money_flow_volume.cumsum()

    return adl