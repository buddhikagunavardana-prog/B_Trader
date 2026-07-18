from __future__ import annotations

import pandas as pd

from src.research.frameworks.state.models import SetupState, SetupStatus
from src.research.frameworks.state.policies.models import PolicyConfiguration, PolicyDecision, PolicyReasonCode


def evaluate_setup_expiration(setup: SetupState, timestamp: pd.Timestamp, session: dict, config: PolicyConfiguration) -> PolicyDecision:
    if setup.status not in {SetupStatus.FORMING, SetupStatus.ARMED}:
        return PolicyDecision(True, PolicyReasonCode.NO_ACTION, "No expirable setup is active.")
    expired = False
    reason = ""
    if config.setup_expiration_mode == "bars" and setup.bars_alive >= config.setup_expiration_bars:
        expired, reason = True, "Configured setup bar lifetime reached."
    elif setup.expiration_timestamp is not None and timestamp >= setup.expiration_timestamp:
        expired, reason = True, "Configured setup expiration timestamp reached."
    elif config.expire_at_entry_cutoff and not session.get("entry_allowed", True):
        return PolicyDecision(False, PolicyReasonCode.SESSION_ENTRY_CUTOFF_REACHED, "Session entry cutoff reached.", "expire_setup")
    if expired:
        return PolicyDecision(False, PolicyReasonCode.SETUP_EXPIRED, reason, "expire_setup", diagnostics={"setup_age": setup.bars_alive})
    return PolicyDecision(True, PolicyReasonCode.ALLOWED, "Setup remains eligible.")


def consume_setup(setup: SetupState, timestamp: pd.Timestamp) -> PolicyDecision:
    if setup.status is SetupStatus.CONSUMED:
        return PolicyDecision(False, PolicyReasonCode.SETUP_ALREADY_CONSUMED, "Setup has already been consumed.")
    if setup.status in {SetupStatus.EXPIRED, SetupStatus.INVALIDATED}:
        return PolicyDecision(False, PolicyReasonCode.MISSING_REQUIRED_SETUP, "No valid setup is available.")
    return PolicyDecision(True, PolicyReasonCode.ALLOWED, "Setup may be consumed.", "consume_setup")
