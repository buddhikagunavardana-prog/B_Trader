def calculate_roc(df, period=12, source="close"):
    roc = ((df[source] - df[source].shift(period)) / df[source].shift(period)) * 100

    return roc