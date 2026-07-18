import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_persistent_event_is_not_repeated():
    c = controller("supertrend_trend_following")
    c.apply(decision(FrameworkSignal.BUY, "supertrend_trend_following"), T0)
    out = c.apply(decision(FrameworkSignal.BUY, "supertrend_trend_following"), T0 + pd.Timedelta(minutes=1))
    assert not out["policy_allowed"] and out["policy_reason_code"] == "REPEATED_ENTRY_SUPPRESSED"


if __name__ == "__main__":
    test_persistent_event_is_not_repeated(); print("test_framework_event_consumption_policy passed")
