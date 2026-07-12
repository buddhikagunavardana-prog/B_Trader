import pandas as pd

from src.strategies.professional.common import buy_signals


def generate_compression_breakout_signals(df: pd.DataFrame, strategy) -> pd.Series:
    period = int(strategy.entry_rules.get("donchian_period", 20))
    squeeze_required = int(strategy.entry_rules.get("squeeze_required", 6))
    squeeze_window = int(strategy.entry_rules.get("squeeze_window", 8))
    relative_volume_min = float(strategy.entry_rules.get("relative_volume_min", 1.3))
    squeeze = (
        (df["BB_UPPER"] < df["KELTNER_UPPER"])
        & (df["BB_LOWER"] > df["KELTNER_LOWER"])
    )
    prior_squeeze_count = squeeze.shift(1).rolling(squeeze_window).sum()
    previous_high = (
        df["DONCHIAN_UPPER"].shift(1)
        if "DONCHIAN_UPPER" in df.columns
        else df["high"].shift(1).rolling(period).max()
    )
    relative_volume = df["volume"] / df["VOL_SMA20"]
    condition = (
        (prior_squeeze_count >= squeeze_required)
        & squeeze.shift(1).fillna(False)
        & (df["close"] > previous_high)
        & (df["close"] > df["BB_UPPER"])
        & (relative_volume >= relative_volume_min)
    )
    return buy_signals(df, condition)
