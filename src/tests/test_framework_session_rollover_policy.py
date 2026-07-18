import pandas as pd
from src.research.frameworks.state import ResearchStateController, SessionConfiguration
from src.research.frameworks.state.models import SessionType
from src.research.frameworks.state.policies import PolicyConfiguration
from src.tests.framework_policy_test_data import T0, decision
from src.trading_frameworks.models import FrameworkSignal


def test_rollover_clears_session_bound_setup():
    session = SessionConfiguration(SessionType.DAILY_SESSION)
    c = ResearchStateController("opening_range_breakout", session=session, policy_configuration=PolicyConfiguration())
    c.apply(decision(FrameworkSignal.HOLD, "opening_range_breakout"), T0)
    out = c.apply(decision(FrameworkSignal.HOLD, "opening_range_breakout"), T0 + pd.Timedelta(days=1))
    assert out["session_rollover"] and "clear_untriggered_setup" in out["session_cleanup_actions"]


if __name__ == "__main__":
    test_rollover_clears_session_bound_setup(); print("test_framework_session_rollover_policy passed")
