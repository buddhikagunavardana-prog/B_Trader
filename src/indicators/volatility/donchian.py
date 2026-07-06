def calculate_donchian_channel(df, period=20):
    upper = df["high"].rolling(window=period).max()
    lower = df["low"].rolling(window=period).min()
    middle = (upper + lower) / 2

    return upper, middle, lower