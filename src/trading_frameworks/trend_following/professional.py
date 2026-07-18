from src.trading_frameworks.rule_based import RuleSpec, build_rule_framework, period, number


ChandelierExitTrendFramework = build_rule_framework(RuleSpec(
    "chandelier_exit_trend", "Chandelier Exit Trend", "trend_following", "chandelier",
    ("chandelier_exit", "ema", "atr"), ("close", "CHANDELIER_LONG", "CHANDELIER_SHORT", "EMA", "ATR"),
    (period("lookback", 22, "Chandelier rolling lookback."), period("atr_period", 22, "ATR period."), number("atr_multiplier", 3, "Chandelier ATR multiple.", .1, 10), period("ema_period", 50, "Trend EMA period.")),
    regimes=("trend",), notes="Prior-completed Chandelier references define entry state and advisory trailing exits; distinct from direction-switching SuperTrend.", state_requirements=("event_consumption", "trailing_exit"), minimum_history=3,
), __name__)

PriceChannelTrendFramework = build_rule_framework(RuleSpec(
    "price_channel_trend", "Price Channel Trend", "trend_following", "price_channel",
    ("price_channels", "ema", "atr"), ("close", "PRICE_CHANNEL_UPPER", "PRICE_CHANNEL_MIDDLE", "PRICE_CHANNEL_LOWER", "EMA", "ATR"),
    (period("channel_period", 20, "Entry price-channel period."), period("ema_period", 50, "Trend EMA period."), period("atr_period", 14, "ATR period.")),
    regimes=("trend", "breakout"), notes="Single-channel prior-value trend event with center-line exit; unlike Turtle dual channels, Donchian-specific naming, or ATR-enveloped Keltner bands.", state_requirements=("event_consumption",), minimum_history=3,
), __name__)

HeikinAshiTrendFramework = build_rule_framework(RuleSpec(
    "heikin_ashi_trend", "Heikin Ashi Trend", "trend_following", "heikin_ashi",
    ("ema", "adx", "atr"), ("open", "high", "low", "close", "HA_OPEN", "HA_HIGH", "HA_LOW", "HA_CLOSE", "EMA", "ADX", "ATR"),
    (period("ema_period", 50, "Trend EMA period."), period("adx_period", 14, "ADX period."), number("minimum_adx", 20, "Minimum ADX.", 0, 100), number("maximum_wick_fraction", .1, "Maximum counter-trend wick as body fraction.", 0, 1), period("atr_period", 14, "ATR period.")),
    regimes=("trend",), notes="Recursively initialized, causal Heikin Ashi state transition with raw-price trend confirmation.", state_requirements=("event_consumption",), minimum_history=3,
), __name__)

AroonTrendFramework = build_rule_framework(RuleSpec(
    "aroon_trend", "Aroon Trend", "trend_following", "aroon",
    ("aroon", "ema", "atr"), ("close", "AROON_UP", "AROON_DOWN", "EMA", "ATR"),
    (period("aroon_period", 25, "Aroon period."), number("strong_threshold", 70, "Strong dominance threshold.", 0, 100), number("weak_threshold", 30, "Weak opposing threshold.", 0, 100), period("ema_period", 50, "Trend EMA period."), period("atr_period", 14, "ATR period.")),
    regimes=("trend",), notes="Aroon dominance transition and neutral-line exit using completed lookbacks.", state_requirements=("event_consumption",), minimum_history=3,
), __name__)

__all__ = ["ChandelierExitTrendFramework", "PriceChannelTrendFramework", "HeikinAshiTrendFramework", "AroonTrendFramework"]
