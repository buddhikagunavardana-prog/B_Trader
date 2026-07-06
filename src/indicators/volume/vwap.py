def calculate_vwap(df):
    typical_price = (df["high"] + df["low"] + df["close"]) / 3

    cumulative_price_volume = (typical_price * df["volume"]).cumsum()
    cumulative_volume = df["volume"].cumsum()

    vwap = cumulative_price_volume / cumulative_volume

    return vwap