import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_columns


def calculate_ease_of_movement(
    df: pd.DataFrame,
    period: int = 14,
    volume_divisor: float = 100_000_000.0,
) -> pd.Series:
    period = positive_int(period, "period")
    volume_divisor = positive_float(volume_divisor, "volume_divisor")
    require_columns(df, ["high", "low", "volume"])
    midpoint_move = ((df["high"] + df["low"]) / 2.0).diff()
    box_ratio = (df["volume"] / volume_divisor) / (df["high"] - df["low"])
    return (midpoint_move / box_ratio).rolling(period).mean().rename("EASE_OF_MOVEMENT")
