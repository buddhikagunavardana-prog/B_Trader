import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_exit_starts_and_enforces_cooldown():
    c = controller("ema_ribbon_trend", cooldown_after_exit_bars=2)
    c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0)
    out = c.apply(decision(FrameworkSignal.EXIT_LONG, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=1))
    assert out["cooldown_active"] and out["cooldown_bars_remaining"] == 2
    blocked = c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=2))
    assert not blocked["policy_allowed"] and blocked["policy_reason_code"] == "COOLDOWN_ACTIVE"
    blocked_again = c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=3))
    assert not blocked_again["policy_allowed"] and blocked_again["cooldown_bars_remaining"] == 0
    allowed = c.apply(decision(FrameworkSignal.BUY, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=4))
    assert allowed["policy_allowed"] and allowed["research_position_state"] == "long_active"


if __name__ == "__main__":
    test_exit_starts_and_enforces_cooldown(); print("test_framework_cooldown_policy passed")
