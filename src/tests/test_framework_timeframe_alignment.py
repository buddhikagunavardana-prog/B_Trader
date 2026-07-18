import pandas as pd

from src.research.frameworks.alignment import alignment_diagnostics, build_causal_alignment
from src.research.frameworks.models import PreparedTimeframeData


def _prepared(role, timeframe, index):
    frame = pd.DataFrame({"close": range(len(index))}, index=index)
    return PreparedTimeframeData(role, timeframe, frame, (), index[0] if len(index) else None, index[-1] if len(index) else None, len(index), 0)


def test_backward_asof_exact_boundaries_gaps_and_timezones():
    primary_index = pd.DatetimeIndex(["2026-01-01 00:59Z", "2026-01-01 01:00Z", "2026-01-01 02:30Z"])
    higher_index = pd.DatetimeIndex(["2026-01-01 00:00Z", "2026-01-01 01:00Z", "2026-01-01 02:00Z"])
    alignment = build_causal_alignment({"entry": _prepared("entry", "5m", primary_index), "trend": _prepared("trend", "1h", higher_index)}, "entry")
    assert alignment.source_timestamps["trend"] == (higher_index[0], higher_index[1], higher_index[2])
    assert alignment_diagnostics(alignment, 0)["trend"].stale_age_seconds == 3540.0
    assert alignment_diagnostics(alignment, 1)["trend"].stale_age_seconds == 0.0
    assert all(source <= timestamp for source, timestamp in zip(alignment.source_timestamps["trend"], alignment.timeline))


if __name__ == "__main__":
    test_backward_asof_exact_boundaries_gaps_and_timezones(); print("test_framework_timeframe_alignment passed")
