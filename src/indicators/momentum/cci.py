def calculate_cci(df, period=20):
    typical_price = (df["high"] + df["low"] + df["close"]) / 3

    sma_tp = typical_price.rolling(window=period).mean()

    mean_deviation = typical_price.rolling(window=period).apply(
        lambda values: abs(values - values.mean()).mean(),
        raw=False
    )

    cci = (typical_price - sma_tp) / (0.015 * mean_deviation)

    return cci