import pandas as pd

from src.strategies.professional.common import buy_signals, indicator_config


def generate_time_series_momentum_signals(df: pd.DataFrame, strategy) -> pd.Series:
    ema = indicator_config(strategy, "ema")
    fast = int(ema.get("fast", 32))
    slow = int(ema.get("slow", 96))
    donchian = int(strategy.entry_rules.get("donchian_period", 20))
    adx_min = float(strategy.entry_rules.get("adx_min", 18))
    previous_high = (
        df["DONCHIAN_UPPER"].shift(1)
        if "DONCHIAN_UPPER" in df.columns
        else df["high"].shift(1).rolling(donchian).max()
    )
    condition = (
        (df["close"] > df[f"EMA{slow}"])
        & (df[f"EMA{fast}"] > df[f"EMA{slow}"])
        & (df[f"EMA{slow}"] > df[f"EMA{slow}"].shift(8))
        & (df["ADX14"] >= adx_min)
        & (df["close"] > previous_high)
    )
    return buy_signals(df, condition)
