from src.indicators.trend.ema import calculate_ema


def calculate_dema(df, period=20, source="close"):
    ema_1 = calculate_ema(df, period=period, source=source)

    temp_df = df.copy()
    temp_df[source] = ema_1

    ema_2 = calculate_ema(temp_df, period=period, source=source)

    return (2 * ema_1) - ema_2