def calculate_vwma(df, period=20, source="close"):
    price_volume = df[source] * df["volume"]

    volume_sum = df["volume"].rolling(window=period).sum()
    price_volume_sum = price_volume.rolling(window=period).sum()

    return price_volume_sum / volume_sum