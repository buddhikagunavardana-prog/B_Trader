from src.indicators.market_strength.aroon import calculate_aroon


def calculate_aroon_oscillator(df, period=25):
    aroon_up, aroon_down = calculate_aroon(df, period)

    return aroon_up - aroon_down