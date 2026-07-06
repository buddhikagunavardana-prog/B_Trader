from src.indicators.trend.ema import calculate_ema


def calculate_tema(df, period=20, source="close"):
    ema_1 = calculate_ema(df, period=period, source=source)

    temp_df_1 = df.copy()
    temp_df_1[source] = ema_1
    ema_2 = calculate_ema(temp_df_1, period=period, source=source)

    temp_df_2 = df.copy()
    temp_df_2[source] = ema_2
    ema_3 = calculate_ema(temp_df_2, period=period, source=source)

    return (3 * ema_1) - (3 * ema_2) + ema_3