import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal
from src.research.frameworks.state.policies.framework_policies import rsi_pullback_transition


def test_rsi_setup_consumes_once():
    c = controller("rsi_pullback_trend", setup_expiration_bars=5)
    c.apply(decision(FrameworkSignal.HOLD, "rsi_pullback_trend"), T0)
    out = c.apply(decision(FrameworkSignal.BUY, "rsi_pullback_trend"), T0 + pd.Timedelta(minutes=1))
    repeated = c.apply(decision(FrameworkSignal.BUY, "rsi_pullback_trend"), T0 + pd.Timedelta(minutes=2))
    assert out["setup_state"] == "consumed" and repeated["policy_reason_code"] == "REPEATED_ENTRY_SUPPRESSED"
    assert rsi_pullback_transition("none", trend_valid=True, setup_crossed=True, recovery_crossed=False, age=0, expiry_bars=5)[0] == "armed"
    assert rsi_pullback_transition("armed", trend_valid=False, setup_crossed=False, recovery_crossed=True, age=1, expiry_bars=5)[0] == "invalidated"


if __name__ == "__main__":
    test_rsi_setup_consumes_once(); print("test_rsi_pullback_policy passed")
