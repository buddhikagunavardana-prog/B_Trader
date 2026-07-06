def calculate_momentum(df, period=10, source="close"):
    momentum = df[source] - df[source].shift(period)

    return momentum