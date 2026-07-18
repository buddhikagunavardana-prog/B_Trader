from __future__ import annotations

from src.research.frameworks.state.models import PositionStatus, SetupStatus
from src.research.frameworks.state.policies.models import PolicyConfiguration, PolicyDecision, PolicyReasonCode


def evaluate_rollover(previous_session_id, current_session_id, position, setup, config: PolicyConfiguration) -> PolicyDecision:
    if previous_session_id is None or previous_session_id == current_session_id:
        return PolicyDecision(True, PolicyReasonCode.NO_ACTION, "No session rollover.")
    actions = []
    if config.clear_untriggered_setups_on_rollover and setup.status in {SetupStatus.FORMING, SetupStatus.ARMED}:
        actions.append("clear_untriggered_setup")
    if config.clear_consumed_setups_on_rollover and setup.status is SetupStatus.CONSUMED:
        actions.append("clear_consumed_setup")
    if config.clear_cooldown_on_rollover and position.status is PositionStatus.COOLDOWN:
        actions.append("clear_cooldown")
    if config.request_exit_at_session_close and not config.carry_active_position_across_sessions and position.status in {PositionStatus.LONG_ACTIVE, PositionStatus.SHORT_ACTIVE}:
        actions.append("request_position_exit")
    return PolicyDecision(True, PolicyReasonCode.SESSION_ROLLOVER_RESET, "Session rollover policy evaluated.", "rollover", diagnostics={"prior_session_id": previous_session_id, "new_session_id": current_session_id, "cleanup_actions": actions})
