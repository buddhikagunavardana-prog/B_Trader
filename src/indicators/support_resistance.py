def calculate_support_resistance(df, period=20):
    support = df["low"].rolling(period).min()
    resistance = df["high"].rolling(period).max()
    return support, resistance