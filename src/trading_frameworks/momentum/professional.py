from src.trading_frameworks.rule_based import RuleSpec, build_rule_framework, period, number


ElderImpulseSystemFramework = build_rule_framework(RuleSpec(
    "elder_impulse_system", "Elder Impulse System", "momentum", "elder_impulse",
    ("ema", "macd", "atr", "adx"), ("close", "EMA", "MACD_HISTOGRAM", "ATR", "ADX"),
    (period("ema_period", 13, "Impulse EMA period."), period("fast_period", 12, "MACD fast period."), period("slow_period", 26, "MACD slow period."), period("signal_period", 9, "MACD signal period."), period("atr_period", 14, "ATR period."), number("minimum_adx", 20, "Optional trend-strength threshold.", 0, 100)),
    regimes=("trend", "momentum"), notes="Alexander Elder impulse-state reference using causal EMA slope and MACD histogram change.", state_requirements=("event_consumption", "opposite_signal_policy"), minimum_history=3,
), __name__)

StochasticPullbackTrendFramework = build_rule_framework(RuleSpec(
    "stochastic_pullback_trend", "Stochastic Pullback Trend", "momentum", "stochastic_pullback",
    ("stochastic", "ema", "adx", "atr"), ("close", "STOCHASTIC_K", "STOCHASTIC_D", "EMA", "ADX", "ATR"),
    (period("k_period", 14, "Stochastic K period."), period("d_period", 3, "Stochastic D period."), period("ema_period", 50, "Trend EMA period."), number("minimum_adx", 20, "Minimum ADX.", 0, 100), number("long_pullback", 25, "Long pullback zone.", 0, 100), number("short_pullback", 75, "Short rally zone.", 0, 100), period("setup_expiry_bars", 5, "Maximum setup age."), period("atr_period", 14, "ATR period.")),
    regimes=("trend",), notes="Trend-qualified stochastic pullback followed by a completed K/D recovery crossing.", state_requirements=("setup", "setup_expiration", "event_consumption"), minimum_history=7,
), __name__)

CciTrendPullbackFramework = build_rule_framework(RuleSpec(
    "cci_trend_pullback", "CCI Trend Pullback", "momentum", "cci_pullback",
    ("cci", "ema", "adx", "atr"), ("close", "CCI", "EMA", "ADX", "ATR"),
    (period("cci_period", 20, "CCI period."), period("ema_period", 50, "Trend EMA period."), number("minimum_adx", 20, "Minimum ADX.", 0, 100), number("long_setup", -100, "Long setup threshold.", -300, 0), number("long_trigger", -50, "Long recovery trigger.", -200, 100), number("short_setup", 100, "Short setup threshold.", 0, 300), number("short_trigger", 50, "Short recovery trigger.", -100, 200), period("setup_expiry_bars", 5, "Maximum setup age."), period("atr_period", 14, "ATR period.")),
    regimes=("trend",), notes="Trend-qualified causal CCI pullback and recovery lifecycle.", state_requirements=("setup", "setup_expiration", "event_consumption"), minimum_history=7,
), __name__)

__all__ = ["ElderImpulseSystemFramework", "StochasticPullbackTrendFramework", "CciTrendPullbackFramework"]
