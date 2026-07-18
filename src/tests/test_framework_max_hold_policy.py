import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_max_hold_requests_research_exit():
    c = controller("zscore_mean_reversion", max_hold_enforcement=True, max_hold_bars=2)
    c.apply(decision(FrameworkSignal.BUY, "zscore_mean_reversion"), T0)
    c.apply(decision(FrameworkSignal.HOLD, "zscore_mean_reversion"), T0 + pd.Timedelta(minutes=1))
    out = c.apply(decision(FrameworkSignal.HOLD, "zscore_mean_reversion"), T0 + pd.Timedelta(minutes=2))
    assert out["max_hold_reached"] and out["policy_reason_code"] == "MAX_HOLD_REACHED" and out["research_position_state"] == "flat"


if __name__ == "__main__":
    test_max_hold_requests_research_exit(); print("test_framework_max_hold_policy passed")
