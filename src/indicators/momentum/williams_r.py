def calculate_williams_r(df, period=14):
    highest_high = df["high"].rolling(window=period).max()
    lowest_low = df["low"].rolling(window=period).min()

    williams_r = -100 * (
        (highest_high - df["close"]) / (highest_high - lowest_low)
    )

    return williams_r