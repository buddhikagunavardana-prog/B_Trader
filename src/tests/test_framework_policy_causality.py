import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def run(signals):
    c = controller("rsi_pullback_trend", setup_expiration_bars=4)
    return [c.apply(decision(signal, "rsi_pullback_trend"), T0 + pd.Timedelta(minutes=i))["policy_reason_code"] for i, signal in enumerate(signals)]


def test_future_changes_do_not_change_policy_prefix():
    prefix = [FrameworkSignal.HOLD, FrameworkSignal.BUY]
    assert run(prefix + [FrameworkSignal.HOLD, FrameworkSignal.SELL])[:2] == run(prefix + [FrameworkSignal.SELL, FrameworkSignal.HOLD])[:2]


if __name__ == "__main__":
    test_future_changes_do_not_change_policy_prefix(); print("test_framework_policy_causality passed")
