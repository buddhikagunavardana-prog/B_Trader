import pandas as pd
from src.research.frameworks.profiling.session import SessionRuntimeContext
from src.research.frameworks.state.session_state import SessionConfiguration, session_snapshot


def test_framework_session_context_cache():
    timeline = pd.date_range("2026-03-07 22:00", periods=80, freq="30min", tz="UTC")
    configuration = SessionConfiguration(timezone="America/New_York", start="18:00", end="17:00")
    cached = SessionRuntimeContext.build(timeline, configuration)
    assert len(cached.snapshots) == len(timeline)
    for index in (0, 10, 40, 79):
        assert dict(cached.snapshots[index]) == session_snapshot(timeline[index], configuration)


if __name__ == "__main__":
    test_framework_session_context_cache(); print("test_framework_session_context_cache passed")
