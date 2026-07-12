import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_elder_ray(
    df: pd.DataFrame,
    period: int = 13,
) -> tuple[pd.Series, pd.Series]:
    period = positive_int(period, "period")
    require_columns(df, ["high", "low", "close"])
    ema = df["close"].ewm(span=period, adjust=False).mean()
    return (df["high"] - ema).rename("BULL_POWER"), (df["low"] - ema).rename(
        "BEAR_POWER",
    )
