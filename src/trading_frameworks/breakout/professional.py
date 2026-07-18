from src.trading_frameworks.rule_based import RuleSpec, build_rule_framework, period, number


MomentumAccelerationBreakoutFramework = build_rule_framework(RuleSpec(
    "momentum_acceleration_breakout", "Momentum Acceleration Breakout", "breakout", "momentum_acceleration",
    ("price_channels", "roc", "momentum", "atr", "ema"), ("close", "PRICE_CHANNEL_UPPER", "PRICE_CHANNEL_MIDDLE", "PRICE_CHANNEL_LOWER", "ROC", "MOMENTUM", "ATR", "EMA"),
    (period("channel_period", 20, "Prior breakout channel period."), period("roc_period", 10, "ROC period."), period("momentum_period", 10, "Momentum period."), number("minimum_roc", 1, "Minimum absolute ROC.", 0, 100), period("ema_period", 50, "Trend EMA period."), period("atr_period", 14, "ATR period."), period("setup_expiry_bars", 3, "False-break invalidation window.")),
    regimes=("breakout", "trend"), notes="Prior-channel breakout confirmed by causal rate-of-change acceleration.", state_requirements=("setup", "setup_expiration", "event_consumption", "false_break_invalidation"), minimum_history=3,
), __name__)

VolumeExpansionBreakoutFramework = build_rule_framework(RuleSpec(
    "volume_expansion_breakout", "Volume Expansion Breakout", "breakout", "volume_expansion",
    ("price_channels", "volume_sma", "atr", "ema"), ("close", "volume", "PRICE_CHANNEL_UPPER", "PRICE_CHANNEL_MIDDLE", "PRICE_CHANNEL_LOWER", "VOLUME_SMA", "ATR", "EMA"),
    (period("channel_period", 20, "Prior breakout channel period."), period("volume_period", 20, "Volume average period."), number("relative_volume_threshold", 1.5, "Minimum relative volume.", 0, 20), period("ema_period", 50, "Trend EMA period."), period("atr_period", 14, "ATR period."), period("setup_expiry_bars", 3, "False-break invalidation window.")),
    regimes=("breakout",), notes="Prior-channel breakout gated by safe relative volume; zero or missing volume cannot confirm.", state_requirements=("setup", "setup_expiration", "event_consumption", "false_break_invalidation"), minimum_history=3,
), __name__)

PivotRangeBreakoutFramework = build_rule_framework(RuleSpec(
    "pivot_range_breakout", "Pivot Range Breakout", "breakout", "pivot_range",
    ("pivot_points", "atr", "ema"), ("close", "PRIOR_PIVOT", "PRIOR_PIVOT_R1", "PRIOR_PIVOT_S1", "PRIOR_SESSION_ID", "ATR", "EMA"),
    (period("level_validity_sessions", 1, "Prior-level validity in sessions."), period("ema_period", 50, "Trend EMA period."), period("atr_period", 14, "ATR period."), period("setup_expiry_bars", 96, "Session setup expiration bars.")),
    regimes=("breakout", "session"), notes="Prior completed-session pivot breakout; unlike Opening Range it never derives levels from the active session.", state_requirements=("setup", "session", "session_rollover", "event_consumption"), minimum_history=3,
), __name__)

__all__ = ["MomentumAccelerationBreakoutFramework", "VolumeExpansionBreakoutFramework", "PivotRangeBreakoutFramework"]
