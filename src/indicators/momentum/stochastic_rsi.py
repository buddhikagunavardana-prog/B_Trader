from src.indicators.momentum.rsi import calculate_rsi


def calculate_stochastic_rsi(df, rsi_period=14, stoch_period=14, d_period=3):
    rsi = calculate_rsi(df, period=rsi_period)

    lowest_rsi = rsi.rolling(window=stoch_period).min()
    highest_rsi = rsi.rolling(window=stoch_period).max()

    stoch_rsi_k = 100 * ((rsi - lowest_rsi) / (highest_rsi - lowest_rsi))
    stoch_rsi_d = stoch_rsi_k.rolling(window=d_period).mean()

    return stoch_rsi_k, stoch_rsi_d