from src.trading_frameworks.rule_based import RuleSpec, build_rule_framework, period, number


ConnorsRsiMeanReversionFramework = build_rule_framework(RuleSpec(
    "connors_rsi_mean_reversion", "Connors RSI Mean Reversion", "mean_reversion", "connors_rsi",
    ("connors_rsi", "ema", "atr"), ("close", "CONNORS_RSI", "EMA", "ATR"),
    (period("rsi_period", 3, "Price RSI component period."), period("streak_period", 2, "Streak RSI component period."), period("rank_period", 100, "Causal percent-rank window."), period("trend_ema_period", 200, "Long-term trend EMA."), number("long_entry", 10, "Long oversold threshold.", 0, 50), number("short_entry", 90, "Short overbought threshold.", 50, 100), number("exit_level", 50, "Mean-reversion exit level.", 1, 99), period("maximum_holding_period", 10, "Advisory maximum-hold hint."), period("atr_period", 14, "ATR period.")),
    regimes=("range", "trend_pullback"), incompatible=("strong_countertrend",), notes="Larry Connors-style three-component RSI using historical percent rank only.", state_requirements=("setup", "setup_expiration", "maximum_hold", "event_consumption"), minimum_history=102,
), __name__)

WilliamsRReversalFramework = build_rule_framework(RuleSpec(
    "williams_r_reversal", "Williams Percent R Reversal", "mean_reversion", "williams_reversal",
    ("williams_r", "ema", "atr"), ("close", "WILLIAMS_R", "EMA", "ATR"),
    (period("williams_period", 14, "Williams %R period."), period("ema_period", 100, "Trend filter EMA."), number("oversold", -80, "Oversold setup threshold.", -100, -1), number("overbought", -20, "Overbought setup threshold.", -99, 0), number("long_recovery", -70, "Long recovery crossing.", -100, 0), number("short_recovery", -30, "Short recovery crossing.", -100, 0), number("exit_level", -50, "Mean exit threshold.", -100, 0), period("setup_expiry_bars", 5, "Maximum setup age."), period("atr_period", 14, "ATR period.")),
    regimes=("range", "trend_pullback"), incompatible=("strong_trend",), notes="Williams %R extreme setup followed by a causal recovery crossing.", state_requirements=("setup", "setup_expiration", "event_consumption"), minimum_history=7,
), __name__)

__all__ = ["ConnorsRsiMeanReversionFramework", "WilliamsRReversalFramework"]
