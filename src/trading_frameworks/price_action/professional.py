from src.trading_frameworks.rule_based import RuleSpec, build_rule_framework, period, number, choice


Nr4Nr7VolatilityBreakoutFramework = build_rule_framework(RuleSpec(
    "nr4_nr7_volatility_breakout", "NR4/NR7 Volatility Breakout", "price_action", "nr_breakout",
    ("true_range", "atr"), ("open", "high", "low", "close", "NR4", "NR7", "ATR"),
    (choice("range_mode", "nr4_or_nr7", ("nr4", "nr7", "nr4_or_nr7"), "Accepted narrow-range setup."), choice("confirmation_mode", "confirmed_close", ("confirmed_close",), "Completed-close trigger."), period("setup_expiry_bars", 3, "Setup expiration bars."), period("atr_period", 14, "ATR period.")),
    regimes=("compression", "breakout"), notes="Completed NR4/NR7 candle setup with stable timestamp ID; distinct from mother-bar containment in Inside Bar.", state_requirements=("setup", "setup_expiration", "event_consumption", "nested_setup"), minimum_history=8,
), __name__)

PinBarRejectionFramework = build_rule_framework(RuleSpec(
    "pin_bar_rejection", "Pin Bar Rejection", "price_action", "pin_bar",
    ("support_resistance", "atr", "ema"), ("open", "high", "low", "close", "SUPPORT", "RESISTANCE", "ATR", "EMA"),
    (number("minimum_wick_ratio", 2, "Minimum rejection wick-to-body ratio.", 1.01, 20), number("maximum_body_ratio", .3, "Maximum body-to-range ratio.", .01, .8), number("level_tolerance_atr", .5, "Confirmed-level tolerance in ATR units.", .01, 10), period("ema_period", 50, "Optional trend EMA period."), period("atr_period", 14, "ATR period."), period("setup_expiry_bars", 2, "Pin setup expiration bars.")),
    optional_dependencies=("rsi",), regimes=("reversal", "range"), notes="Quantitative wick/body rejection at externally confirmed historical support or resistance; stricter than generic level bounce.", state_requirements=("setup", "level", "setup_expiration", "event_consumption"), minimum_history=2,
), __name__)

EngulfingConfirmationTrendFramework = build_rule_framework(RuleSpec(
    "engulfing_confirmation_trend", "Engulfing Confirmation Trend", "price_action", "engulfing",
    ("candlestick", "ema", "adx", "atr"), ("open", "high", "low", "close", "bullish_engulfing", "bearish_engulfing", "EMA", "ADX", "ATR"),
    (choice("engulfing_mode", "strict", ("strict", "relaxed"), "Engulfing-body interpretation."), period("ema_period", 50, "Trend EMA period."), period("adx_period", 14, "ADX period."), number("minimum_adx", 20, "Minimum ADX.", 0, 100), period("atr_period", 14, "ATR period."), period("setup_expiry_bars", 2, "Pattern setup expiration bars.")),
    optional_dependencies=("volume_sma",), regimes=("trend", "pullback"), notes="Completed bullish/bearish engulfing event with explicit trend confirmation and stable pattern ID.", state_requirements=("setup", "setup_expiration", "event_consumption"), minimum_history=3,
), __name__)

__all__ = ["Nr4Nr7VolatilityBreakoutFramework", "PinBarRejectionFramework", "EngulfingConfirmationTrendFramework"]
