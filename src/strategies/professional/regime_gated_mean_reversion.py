import pandas as pd

from src.strategies.professional.common import buy_signals, indicator_config


ALLOWED_REGIMES = {"SIDEWAYS", "LOW_VOLATILITY", "RANGE", "LOW_TREND"}
FORBIDDEN_REGIMES = {"TRENDING", "HIGH_VOLATILITY", "BREAKOUT", "VOLATILITY_SHOCK"}


def generate_regime_mean_reversion_signals(df: pd.DataFrame, strategy) -> pd.Series:
    ema = indicator_config(strategy, "ema")
    fast = int(ema.get("fast", 32))
    slow = int(ema.get("slow", 96))
    rsi_period = int(indicator_config(strategy, "rsi").get("period", 2))
    flatness = (df[f"EMA{fast}"] - df[f"EMA{slow}"]).abs() / df["close"] * 100
    eligible = (
        (df["ADX14"] < float(strategy.entry_rules.get("adx_max", 16)))
        & (flatness <= float(strategy.entry_rules.get("ema_flatness_max_pct", 0.4)))
    )
    if "REGIME" in df.columns:
        regimes = df["REGIME"].astype(str).str.upper()
        eligible &= regimes.isin(ALLOWED_REGIMES) & ~regimes.isin(FORBIDDEN_REGIMES)
    condition = (
        eligible
        & (df["ZSCORE"] <= float(strategy.entry_rules.get("zscore_max", -2.0)))
        & (df["close"] < df["BB_LOWER"])
        & (df[f"RSI{rsi_period}"] <= float(strategy.entry_rules.get("rsi_max", 8)))
        & (df["close"] < df["ROLLING_VWAP"])
    )
    return buy_signals(df, condition)
