import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_conservative_default_requires_exit_before_reversal():
    c = controller("ema_ribbon_trend")
    c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0)
    out = c.apply(decision(FrameworkSignal.SELL, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=1))
    assert out["research_position_state"] == "exit_pending" and out["policy_reason_code"] == "EXIT_REQUIRED_BEFORE_REVERSAL"
    repeated = c.apply(decision(FrameworkSignal.SELL, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=2))
    assert repeated["position_transition"] == "repeated_exit_request_suppressed"
    exited = c.apply(decision(FrameworkSignal.EXIT_LONG, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=3))
    assert exited["research_position_state"] == "flat"


def test_immediate_reversal_requires_explicit_mode():
    c = controller("ema_ribbon_trend", opposite_signal_mode="allow_immediate_reverse")
    c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0)
    out = c.apply(decision(FrameworkSignal.SELL, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=1))
    assert out["research_position_state"] == "short_active" and out["opposite_signal_action"] == "reverse"


if __name__ == "__main__":
    test_conservative_default_requires_exit_before_reversal(); test_immediate_reversal_requires_explicit_mode(); print("test_framework_opposite_signal_policy passed")
