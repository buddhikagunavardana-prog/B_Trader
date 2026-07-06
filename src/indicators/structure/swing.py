def calculate_swing_points(df, period=5):
    swing_high = (
        df["high"]
        == df["high"].rolling(period * 2 + 1, center=True).max()
    )

    swing_low = (
        df["low"]
        == df["low"].rolling(period * 2 + 1, center=True).min()
    )

    return swing_high, swing_low