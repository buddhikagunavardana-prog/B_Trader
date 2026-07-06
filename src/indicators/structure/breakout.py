def calculate_breakout_levels(df, period=20):
    breakout_high = df["high"].rolling(window=period).max()
    breakout_low = df["low"].rolling(window=period).min()

    return breakout_high, breakout_low