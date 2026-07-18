import pandas as pd

from src.indicators._validation import positive_int
from src.indicators.market_strength.directional import calculate_directional_movement


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ADX from shared directional-movement components."""
    period = positive_int(period, "period")
    plus_di, minus_di = calculate_directional_movement(df, period)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.replace([float("inf"), float("-inf")], float("nan")).rolling(period).mean().rename("ADX")
