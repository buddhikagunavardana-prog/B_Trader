import pandas as pd

from src.strategies.professional.common import buy_signals, indicator_config


def generate_trend_pullback_signals(df: pd.DataFrame, strategy) -> pd.Series:
    ema = indicator_config(strategy, "ema")
    entry = int(ema.get("fast", 20))
    trend = int(ema.get("slow", 48))
    structure = int(ema.get("trend", 192))
    rsi_period = int(indicator_config(strategy, "rsi").get("period", 3))
    rsi_max = float(strategy.entry_rules.get("previous_rsi_max", 20))
    condition = (
        (df[f"EMA{trend}"] > df[f"EMA{structure}"])
        & (df[f"EMA{structure}"] > df[f"EMA{structure}"].shift(8))
        & (df["ADX14"] >= float(strategy.entry_rules.get("adx_min", 18)))
        & (df[f"RSI{rsi_period}"].shift(1) <= rsi_max)
        & (df["close"].shift(1) < df[f"EMA{entry}"].shift(1))
        & (df["close"] > df[f"EMA{entry}"])
    )
    return buy_signals(df, condition)
