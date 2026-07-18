STATEFUL_SETUP_FRAMEWORKS = frozenset({
    "inside_bar_breakout", "opening_range_breakout", "rsi_pullback_trend",
    "support_resistance_bounce", "bollinger_squeeze_breakout",
    "connors_rsi_mean_reversion", "stochastic_pullback_trend", "williams_r_reversal",
    "cci_trend_pullback", "momentum_acceleration_breakout", "volume_expansion_breakout",
    "nr4_nr7_volatility_breakout", "pin_bar_rejection",
    "engulfing_confirmation_trend", "pivot_range_breakout",
    "order_block", "fair_value_gap", "break_of_structure", "change_of_character",
    "liquidity_sweep", "equal_high_low_liquidity", "breaker_block", "mitigation_block",
    "premium_discount_zone", "market_structure_shift", "balanced_price_range",
    "displacement", "judas_swing", "kill_zone_setup", "power_of_three",
})

SESSION_BOUND_FRAMEWORKS = frozenset({"opening_range_breakout", "pivot_range_breakout", "judas_swing", "kill_zone_setup", "power_of_three"})
LEVEL_FRAMEWORKS = frozenset({"support_resistance_bounce", "pin_bar_rejection"})
EVENT_FRAMEWORKS = frozenset({
    "parabolic_sar_trend", "dual_moving_average_crossover", "macd_momentum",
    "adx_trend_following", "supertrend_trend_following", "opening_range_breakout",
    "inside_bar_breakout", "bollinger_squeeze_breakout",
    "elder_impulse_system", "chandelier_exit_trend", "price_channel_trend",
    "heikin_ashi_trend", "aroon_trend", "momentum_acceleration_breakout",
    "volume_expansion_breakout", "nr4_nr7_volatility_breakout", "pin_bar_rejection",
    "engulfing_confirmation_trend", "pivot_range_breakout", "stochastic_pullback_trend",
    "williams_r_reversal", "cci_trend_pullback", "connors_rsi_mean_reversion",
    "order_block", "fair_value_gap", "break_of_structure", "change_of_character",
    "liquidity_sweep", "equal_high_low_liquidity", "breaker_block", "mitigation_block",
    "market_structure_shift", "balanced_price_range", "displacement", "judas_swing",
    "kill_zone_setup", "power_of_three",
})


def framework_policy_requirements(framework: str) -> dict[str, bool]:
    return {
        "setup": framework in STATEFUL_SETUP_FRAMEWORKS,
        "session": framework in SESSION_BOUND_FRAMEWORKS,
        "level": framework in LEVEL_FRAMEWORKS,
        "event_consumption": framework in EVENT_FRAMEWORKS,
    }


def opening_range_transition(state: str, *, opening_complete: bool, data_sufficient: bool, entry_allowed: bool, breakout_side: str | None, consumed: bool) -> tuple[str, str]:
    if not data_sufficient:
        return "invalidated", "INSUFFICIENT_OPENING_RANGE"
    if not opening_complete:
        return "forming", "OPENING_RANGE_INCOMPLETE"
    if not entry_allowed:
        return "expired", "SESSION_ENTRY_CUTOFF_REACHED"
    if consumed and breakout_side:
        return "consumed", "SETUP_ALREADY_CONSUMED"
    if breakout_side:
        return "triggered", "ALLOWED"
    return "armed", "NO_ACTION"


def inside_bar_transition(state: str, *, age: int, expiry_bars: int, structural_violation: bool, breakout_side: str | None, nested_policy: str) -> tuple[str, str]:
    if structural_violation:
        return "invalidated", "SETUP_INVALIDATED"
    if age >= expiry_bars:
        return "expired", "SETUP_EXPIRED"
    if state == "consumed" and breakout_side:
        return "consumed", "SETUP_ALREADY_CONSUMED"
    if breakout_side:
        return "triggered", "ALLOWED"
    if nested_policy == "reject_nested_setup" and state == "armed":
        return state, "NESTED_SETUP_REJECTED"
    return "armed", "NO_ACTION"


def rsi_pullback_transition(state: str, *, trend_valid: bool, setup_crossed: bool, recovery_crossed: bool, age: int, expiry_bars: int) -> tuple[str, str]:
    if state == "armed" and not trend_valid:
        return "invalidated", "SETUP_INVALIDATED"
    if state == "armed" and age >= expiry_bars:
        return "expired", "SETUP_EXPIRED"
    if state == "armed" and recovery_crossed:
        return "triggered", "ALLOWED"
    if trend_valid and setup_crossed:
        return "armed", "NO_ACTION"
    return state, "NO_ACTION"


def squeeze_transition(state: str, *, squeeze_active: bool, squeeze_bars: int, minimum_squeeze_bars: int, breakout_side: str | None, release_age: int, maximum_release_to_trigger_bars: int) -> tuple[str, str]:
    if state == "no_squeeze" and squeeze_active:
        return "squeeze_active", "NO_ACTION"
    if state == "squeeze_active" and not squeeze_active and squeeze_bars >= minimum_squeeze_bars:
        return "release_detected", "NO_ACTION"
    if state in {"release_detected", "breakout_armed"} and squeeze_active:
        return "invalidated", "SETUP_INVALIDATED"
    if state in {"release_detected", "breakout_armed"} and release_age > maximum_release_to_trigger_bars:
        return "expired", "SETUP_EXPIRED"
    if state in {"release_detected", "breakout_armed"} and breakout_side:
        return "breakout_triggered", "ALLOWED"
    if state == "release_detected":
        return "breakout_armed", "NO_ACTION"
    return state, "NO_ACTION"
