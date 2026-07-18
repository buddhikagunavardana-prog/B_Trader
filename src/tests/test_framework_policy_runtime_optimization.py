import pandas as pd
from src.research.frameworks.profiling.session import SessionRuntimeContext
from src.research.frameworks.state.controller import ResearchStateController
from src.research.frameworks.state.session_state import SessionConfiguration
from src.trading_frameworks.loader import load_trading_framework
from src.tests.framework_expansion_35_test_data import directional_scenario


def test_framework_policy_runtime_optimization():
    timestamp = pd.Timestamp("2026-01-02", tz="UTC")
    decision = load_trading_framework("elder_impulse_system").execute(directional_scenario("elder_impulse_system", "long"))
    configuration = SessionConfiguration()
    cached = dict(SessionRuntimeContext.build(pd.DatetimeIndex([timestamp]), configuration).snapshots[0])
    direct = ResearchStateController("elder_impulse_system", session=configuration).apply(decision, timestamp)
    optimized = ResearchStateController("elder_impulse_system", session=configuration).apply(decision, timestamp, cached)
    assert direct == optimized


if __name__ == "__main__":
    test_framework_policy_runtime_optimization(); print("test_framework_policy_runtime_optimization passed")
