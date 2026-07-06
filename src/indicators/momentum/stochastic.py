def calculate_stochastic(df, k_period=14, d_period=3):
    lowest_low = df["low"].rolling(window=k_period).min()
    highest_high = df["high"].rolling(window=k_period).max()

    stoch_k = 100 * ((df["close"] - lowest_low) / (highest_high - lowest_low))
    stoch_d = stoch_k.rolling(window=d_period).mean()

    return stoch_k, stoch_d