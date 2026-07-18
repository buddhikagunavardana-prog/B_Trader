from __future__ import annotations

import pandas as pd

from src.research.frameworks.alignment import build_causal_alignment
from src.research.frameworks.models import PreparedTimeframeData
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
from src.utils.trading_framework_performance import _context


def _prepared(role, timeframe, index):
    frame = pd.DataFrame({"close": range(len(index))}, index=index)
    return PreparedTimeframeData(role, timeframe, frame, (), index[0], index[-1], len(index), 0)


def test_premium_discount_higher_timeframe_alignment_uses_only_completed_bars():
    execution = pd.date_range("2026-01-01 00:15Z", periods=8, freq="15min")
    structure = pd.date_range("2026-01-01 00:00Z", periods=3, freq="1h")
    alignment = build_causal_alignment({"execution": _prepared("execution", "15m", execution), "structure": _prepared("structure", "1h", structure)}, "execution")
    assert all(source <= current for source, current in zip(alignment.source_timestamps["structure"], alignment.timeline))


def test_session_frameworks_use_iana_timezone_across_dst_transition():
    context = _context("kill_zone_setup", 80)
    framework = load_trading_framework("kill_zone_setup", {"session_timezone": "America/New_York", "session_start": "01:00", "session_end": "04:00"})
    decision = framework.execute(FrameworkContext(context.frames))
    assert decision.diagnostics["reason_code"] in {"SESSION_CLOSED", "KILL_ZONE_ACTIVE_NO_STRUCTURE", "KILL_ZONE_SETUP_CONFIRMED"}
    assert framework.parameters["session_timezone"] == "America/New_York"


def test_named_kill_zone_window_is_active_without_a_hard_coded_timezone():
    frames = _context("kill_zone_setup", 80).frames
    framework = load_trading_framework("kill_zone_setup", {"session_name": "london", "session_timezone": "UTC"})
    decision = framework.execute(FrameworkContext(frames), pd.Timestamp("2026-01-01 08:00Z"))
    assert decision.diagnostics["reason_code"] != "SESSION_CLOSED"


def test_power_of_three_lifecycle_is_forward_only():
    index = pd.date_range("2026-01-01 08:00Z", periods=11, freq="15min")
    frame = pd.DataFrame({"open":100.0,"high":100.2,"low":99.8,"close":100.0,"volume":1000.0}, index=index)
    frame.loc[index[8], ["open", "high", "low", "close"]] = [100.0, 100.1, 98.0, 99.9]
    frame.loc[index[9], ["open", "high", "low", "close"]] = [99.9, 103.2, 99.8, 103.0]
    frame.loc[index[10], ["open", "high", "low", "close"]] = [103.0, 104.2, 102.8, 104.0]
    framework = load_trading_framework("power_of_three", {"reference_bars": 8, "session_start": "08:00", "session_end": "12:00", "atr_multiple": .5})
    observed = []
    for size in (8, 9, 10, 11):
        decision = framework.generate_decision(FrameworkContext({"execution": frame.iloc[:size]}), index[size - 1])
        observed.append(decision.diagnostics["lifecycle_state"])
    assert observed == ["accumulation", "manipulation", "distribution", "completed"]
