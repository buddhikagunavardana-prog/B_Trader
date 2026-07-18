from __future__ import annotations

import pandas as pd

from src.research.frameworks.state.models import PositionState, PositionStatus
from src.research.frameworks.state.policies.models import OppositeSignalMode, PolicyConfiguration, PolicyDecision, PolicyReasonCode


def evaluate_entry(position: PositionState, signal: str, config: PolicyConfiguration) -> PolicyDecision:
    if position.status is PositionStatus.COOLDOWN:
        return PolicyDecision(False, PolicyReasonCode.COOLDOWN_ACTIVE, "Entry rejected while cooldown is active.")
    if position.status is PositionStatus.EXIT_PENDING:
        return PolicyDecision(False, PolicyReasonCode.EXIT_REQUIRED_BEFORE_REVERSAL, "An exit request is already pending.", "request_exit")
    same = (position.status is PositionStatus.LONG_ACTIVE and signal == "buy") or (position.status is PositionStatus.SHORT_ACTIVE and signal == "sell")
    if same:
        return PolicyDecision(False, PolicyReasonCode.REPEATED_ENTRY_SUPPRESSED, "Persistent same-side entry was suppressed.")
    opposite = (position.status is PositionStatus.LONG_ACTIVE and signal == "sell") or (position.status is PositionStatus.SHORT_ACTIVE and signal == "buy")
    if not opposite:
        return PolicyDecision(True, PolicyReasonCode.ALLOWED, "Entry transition is legal.", "enter")
    mode = config.opposite_signal_mode
    if mode is OppositeSignalMode.IGNORE:
        return PolicyDecision(False, PolicyReasonCode.OPPOSITE_SIGNAL_IGNORED, "Opposite signal ignored by policy.")
    if mode is OppositeSignalMode.REJECT:
        return PolicyDecision(False, PolicyReasonCode.OPPOSITE_SIGNAL_REJECTED, "Opposite signal rejected by policy.")
    if mode in {OppositeSignalMode.REQUEST_EXIT, OppositeSignalMode.EXIT_THEN_REVERSE}:
        return PolicyDecision(False, PolicyReasonCode.EXIT_REQUIRED_BEFORE_REVERSAL, "Exit is required before reversal.", "request_exit")
    return PolicyDecision(True, PolicyReasonCode.IMMEDIATE_REVERSAL_ALLOWED, "Explicit policy allows immediate reversal.", "reverse")


def evaluate_max_hold(position: PositionState, timestamp: pd.Timestamp, config: PolicyConfiguration) -> PolicyDecision:
    if not config.max_hold_enforcement or position.status not in {PositionStatus.LONG_ACTIVE, PositionStatus.SHORT_ACTIVE}:
        return PolicyDecision(True, PolicyReasonCode.NO_ACTION, "Maximum-hold enforcement is inactive.")
    bars_reached = config.max_hold_bars is not None and position.bars_since_entry_signal >= config.max_hold_bars
    duration_reached = False
    if config.max_hold_duration and position.activation_timestamp is not None:
        duration_reached = timestamp - position.activation_timestamp >= pd.Timedelta(config.max_hold_duration)
    if bars_reached or duration_reached:
        return PolicyDecision(False, PolicyReasonCode.MAX_HOLD_REACHED, "Maximum holding period reached.", "request_exit")
    return PolicyDecision(True, PolicyReasonCode.ALLOWED, "Maximum holding period not reached.")
