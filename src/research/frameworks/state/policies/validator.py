from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyValidationIssue:
    code: str
    severity: str
    message: str


def validate_policy_rows(frame):
    issues = []
    required = {"policy_allowed", "policy_reason_code", "research_position_state", "position_transition"}
    missing = required - set(frame.columns)
    if missing:
        issues.append(PolicyValidationIssue("MISSING_POLICY_FIELDS", "ERROR", ", ".join(sorted(missing))))
        return tuple(issues)
    if frame["policy_reason_code"].isna().any() or (frame["policy_reason_code"] == "").any():
        issues.append(PolicyValidationIssue("MISSING_REASON_CODE", "ERROR", "Every stateful row requires a reason code."))
    illegal = frame["position_transition"].astype(str).str.contains("long_active->short_active|short_active->long_active", regex=True)
    immediate = frame.get("opposite_signal_action", "") == "reverse"
    if (illegal & ~immediate).any():
        issues.append(PolicyValidationIssue("ILLEGAL_REVERSAL", "ERROR", "Direct reversal occurred without explicit permission."))
    return tuple(issues)
