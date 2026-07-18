from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_expired_setup_cannot_trigger():
    c = controller(setup_expiration_bars=1)
    c.apply(decision(FrameworkSignal.HOLD), T0)
    row = c.apply(decision(FrameworkSignal.BUY), T0 + __import__("pandas").Timedelta(minutes=1))
    assert row["setup_state"] == "expired" and not row["policy_allowed"] and row["policy_reason_code"] == "SETUP_EXPIRED"


if __name__ == "__main__":
    test_expired_setup_cannot_trigger(); print("test_framework_setup_expiration_policy passed")
