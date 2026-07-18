from __future__ import annotations

import json
from math import isfinite
from typing import Mapping

import pandas as pd

from src.research.frameworks.models import ResearchValidationIssue, ResearchValidationResult


DECISION_COLUMNS = (
    "timestamp", "framework", "framework_version", "signal", "direction",
    "entry_allowed", "exit_requested", "confidence", "entry_reason", "exit_reason",
    "stop_type", "stop_value", "stop_distance", "target_type", "target_value",
    "reward_to_risk", "trailing_stop_type", "risk_fraction_suggestion",
    "maximum_holding_period", "diagnostics", "warnings", "rows_available",
    "warmup_complete", "decision_valid", "skip_reason",
)

STATE_COLUMNS=("research_position_state","previous_position_state","position_transition","bars_in_position_state","setup_state","previous_setup_state","setup_id","setup_age","setup_transition","session_id","session_state","session_open","session_close","opening_range_complete","state_warning","state_valid","policy_allowed","policy_reason_code","policy_reason","setup_expiration_reason","setup_invalidation_reason","opposite_signal_action","cooldown_active","cooldown_bars_remaining","max_hold_reached","session_rollover","session_cleanup_actions","level_id","level_state","level_test_count","level_retest_allowed","controller_time_ns","policy_time_ns")


def validate_decision_series(frame: pd.DataFrame) -> ResearchValidationResult:
    issues: list[ResearchValidationIssue] = []
    missing = [column for column in DECISION_COLUMNS if column not in frame.columns]
    if missing:
        issues.append(ResearchValidationIssue("missing_columns", "ERROR", ", ".join(missing)))
        return ResearchValidationResult(tuple(issues))
    if not frame["timestamp"].is_monotonic_increasing or frame["timestamp"].duplicated().any():
        issues.append(ResearchValidationIssue("invalid_timeline", "ERROR", "timestamps must be unique and chronological"))
    if not set(frame["signal"]).issubset({"buy", "sell", "exit_long", "exit_short", "hold", "no_trade"}):
        issues.append(ResearchValidationIssue("invalid_signal", "ERROR", "unknown signal value"))
    if not set(frame["direction"]).issubset({"long", "short", "flat"}):
        issues.append(ResearchValidationIssue("invalid_direction", "ERROR", "unknown direction value"))
    for column in ("confidence", "stop_value", "stop_distance", "target_value", "reward_to_risk", "risk_fraction_suggestion"):
        values = frame[column].dropna()
        if any(not isfinite(float(value)) for value in values):
            issues.append(ResearchValidationIssue("nonfinite_output", "ERROR", f"non-finite {column}"))
    for column in ("diagnostics", "warnings", "rows_available"):
        try:
            for value in frame[column]: json.loads(value)
        except (TypeError, json.JSONDecodeError):
            issues.append(ResearchValidationIssue("invalid_json", "ERROR", f"{column} is not JSON-safe"))
    invalid_skips = frame[(~frame["decision_valid"]) & (frame["skip_reason"].str.len() == 0)]
    if len(invalid_skips):
        issues.append(ResearchValidationIssue("missing_skip_reason", "ERROR", "invalid rows require a skip reason"))
    if len(frame) > 2:
        gaps = frame["timestamp"].diff().dropna().dt.total_seconds()
        median = gaps.median()
        if median > 0 and (gaps > median * 3).any():
            issues.append(ResearchValidationIssue("timeline_gap", "WARNING", "primary timeline contains a gap greater than three intervals"))
    if "policy_reason_code" in frame and ((frame["policy_reason_code"].isna()) | (frame["policy_reason_code"] == "")).any():
        issues.append(ResearchValidationIssue("missing_policy_reason_code", "ERROR", "stateful rows require machine-readable policy reason codes"))
    return ResearchValidationResult(tuple(issues))


def validate_repeatability(first: pd.DataFrame, second: pd.DataFrame) -> ResearchValidationResult:
    try:
        pd.testing.assert_frame_equal(first, second, check_exact=True)
    except AssertionError as error:
        return ResearchValidationResult((ResearchValidationIssue("nondeterministic", "ERROR", str(error)),))
    return ResearchValidationResult(())
