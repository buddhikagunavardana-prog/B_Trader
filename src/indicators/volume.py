def calculate_volume_sma(df, period=20):
    return df["volume"].rolling(period).mean()