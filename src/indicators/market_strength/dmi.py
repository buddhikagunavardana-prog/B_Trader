import pandas as pd

from src.indicators.market_strength.directional import calculate_directional_movement


def calculate_dmi(
    df: pd.DataFrame, period: int = 14,
) -> tuple[pd.Series, pd.Series]:
    """Calculate shared positive and negative directional movement."""
    plus, minus = calculate_directional_movement(df, period)
    return plus.rename("DMI_PLUS"), minus.rename("DMI_MINUS")
