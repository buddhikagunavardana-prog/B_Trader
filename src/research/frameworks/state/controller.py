from __future__ import annotations

from dataclasses import replace
from time import perf_counter_ns
from typing import Any

import pandas as pd

from src.research.frameworks.state.models import PositionState, PositionStatus, SetupState, SetupStatus, StateSnapshot
from src.research.frameworks.state.policies.framework_policies import EVENT_FRAMEWORKS, SESSION_BOUND_FRAMEWORKS, STATEFUL_SETUP_FRAMEWORKS
from src.research.frameworks.state.policies.models import PolicyConfiguration, PolicyReasonCode, PolicyTimingSummary
from src.research.frameworks.state.policies.position_policies import evaluate_entry, evaluate_max_hold
from src.research.frameworks.state.policies.session_policies import evaluate_rollover
from src.research.frameworks.state.policies.setup_policies import evaluate_setup_expiration
from src.research.frameworks.state.session_state import SessionConfiguration, session_snapshot
from src.research.frameworks.profiling.models import SnapshotMode


class ResearchStateController:
    """Owns research-only lifecycle transitions after a framework proposes a decision."""

    def __init__(
        self, framework: str, session: SessionConfiguration | None = None, cooldown_bars: int = 0,
        allow_repeated_entries: bool = False, reverse_on_opposite_signal: bool = False,
        policy_configuration: PolicyConfiguration | dict[str, Any] | None = None,
        snapshot_mode: SnapshotMode | str = SnapshotMode.NONE,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self.framework = framework
        self.position = PositionState(framework=framework)
        self.setup = SetupState(framework=framework)
        self.session_config = session or SessionConfiguration()
        self.allow_repeated = allow_repeated_entries
        if isinstance(policy_configuration, PolicyConfiguration):
            policy = policy_configuration
        else:
            policy = PolicyConfiguration.from_mapping(policy_configuration)
        legacy = {}
        if cooldown_bars and not policy.cooldown_after_exit_bars:
            legacy["cooldown_after_exit_bars"] = cooldown_bars
        if reverse_on_opposite_signal:
            legacy["opposite_signal_mode"] = "allow_immediate_reverse"
        self.policy = PolicyConfiguration.from_mapping({**policy.to_dict(), **legacy})
        self.is_setup_framework = framework in STATEFUL_SETUP_FRAMEWORKS
        self.is_event_framework = framework in EVENT_FRAMEWORKS
        self.is_session_bound = framework in SESSION_BOUND_FRAMEWORKS
        self.rollover_policy = self.policy if self.is_session_bound else replace(
            self.policy,
            clear_untriggered_setups_on_rollover=False,
            clear_consumed_setups_on_rollover=False,
        )
        self.snapshot_mode = SnapshotMode(snapshot_mode)
        self.stored_snapshots: list[dict[str, Any]] = []
        self.setup.maximum_bars_alive = self.policy.setup_expiration_bars
        self.previous_session_id: str | None = None
        self.last_event_side: str | None = None
        self.event_reset = True
        self.last_timing = PolicyTimingSummary()
        self.timing_totals = {key: 0 for key in PolicyTimingSummary.__dataclass_fields__}
        if initial_state:
            self.restore(initial_state)

    def restore(self, state: dict[str, Any]) -> None:
        """Restore explicit JSON-compatible continuity state for a new chunk."""
        position = dict(state.get("position", {}))
        setup = dict(state.get("setup", {}))
        if position:
            position["status"] = PositionStatus(position.get("status", "flat"))
            for key in ("entry_signal_timestamp", "activation_timestamp", "exit_request_timestamp", "cooldown_started_at"):
                if position.get(key) is not None:
                    position[key] = pd.Timestamp(position[key])
            self.position = PositionState(**{key: value for key, value in position.items() if key in PositionState.__dataclass_fields__})
        if setup:
            setup["status"] = SetupStatus(setup.get("status", "none"))
            for key in ("created_timestamp", "armed_timestamp", "trigger_timestamp", "expiration_timestamp", "consumed_timestamp"):
                if setup.get(key) is not None:
                    setup[key] = pd.Timestamp(setup[key])
            self.setup = SetupState(**{key: value for key, value in setup.items() if key in SetupState.__dataclass_fields__})
        continuity = state.get("continuity", {})
        self.previous_session_id = continuity.get("previous_session_id")
        self.last_event_side = continuity.get("last_event_side")
        self.event_reset = bool(continuity.get("event_reset", True))

    def snapshot(self, timestamp: pd.Timestamp, session: dict[str, Any] | None = None) -> StateSnapshot:
        return StateSnapshot(self.position.to_dict(), self.setup.to_dict(), session or session_snapshot(timestamp, self.session_config))

    def _start_cooldown(self, bars: int, timestamp: pd.Timestamp, reason: str) -> None:
        if bars <= 0:
            self.position.status = PositionStatus.FLAT
            return
        self.position.status = PositionStatus.COOLDOWN
        self.position.cooldown_reason = reason
        self.position.cooldown_bars_total = bars
        self.position.cooldown_bars_remaining = bars
        self.position.cooldown_started_at = timestamp

    def _clear_setup(self, reason: str = "") -> None:
        self.setup = SetupState(framework=self.framework, reason=reason, maximum_bars_alive=self.policy.setup_expiration_bars)

    def _exit(self, timestamp: pd.Timestamp, reason: str) -> str:
        previous = self.position.status
        self.position.exit_request_timestamp = timestamp
        self.position.latest_exit_reason = reason
        self.position.direction = "flat"
        self._start_cooldown(self.policy.cooldown_after_exit_bars, timestamp, reason)
        return f"{previous.value}->{self.position.status.value}"

    def _enter(self, signal: str, decision: Any, timestamp: pd.Timestamp) -> str:
        previous = self.position.status
        self.position.status = PositionStatus.LONG_ACTIVE if signal == "buy" else PositionStatus.SHORT_ACTIVE
        self.position.direction = "long" if signal == "buy" else "short"
        self.position.entry_signal_timestamp = timestamp
        self.position.activation_timestamp = timestamp
        self.position.entry_reason = decision.entry_reason
        self.position.bars_in_state = 0
        self.position.bars_since_entry_signal = 0
        self.position.maximum_holding_period = decision.risk.maximum_holding_period
        self.position.stop_proposal = {"type": decision.risk.stop_type, "value": decision.risk.stop_loss, "distance": decision.risk.stop_distance}
        self.position.target_proposal = {"type": decision.risk.take_profit_type, "value": decision.risk.take_profit, "reward_to_risk": decision.risk.reward_to_risk}
        self.position.trailing_proposal = {"type": decision.risk.trailing_stop_type}
        return f"{previous.value}->{self.position.status.value}"

    def apply(self, decision: Any, timestamp: pd.Timestamp, session_context: dict[str, Any] | None = None) -> dict[str, Any]:
        total_started = perf_counter_ns() if self.policy.enable_controller_timing else 0
        timestamp = pd.Timestamp(timestamp)
        previous_position = self.position.status
        previous_setup = self.setup.status
        signal = decision.signal.value
        transition = "none"
        setup_transition = "none"
        reason_code = PolicyReasonCode.NO_ACTION
        reason = "No policy action required."
        policy_allowed = True
        opposite_action = "none"
        cleanup_actions: list[str] = []
        session_rollover = False
        max_hold_reached = False

        session_started = perf_counter_ns() if self.policy.enable_controller_timing else 0
        session = session_context or session_snapshot(timestamp, self.session_config)
        rollover = evaluate_rollover(self.previous_session_id, session["session_id"], self.position, self.setup, self.rollover_policy)
        if rollover.reason_code is PolicyReasonCode.SESSION_ROLLOVER_RESET:
            session_rollover = True
            cleanup_actions = list(rollover.diagnostics.get("cleanup_actions", []))
            if "clear_untriggered_setup" in cleanup_actions or "clear_consumed_setup" in cleanup_actions:
                self._clear_setup("session rollover")
            if "clear_cooldown" in cleanup_actions:
                self.position.status = PositionStatus.FLAT
                self.position.cooldown_bars_remaining = 0
            if "request_position_exit" in cleanup_actions:
                transition = self._exit(timestamp, "Session rollover exit policy.")
                reason_code, reason = rollover.reason_code, rollover.reason
        self.previous_session_id = session["session_id"]
        session_ns = perf_counter_ns() - session_started if self.policy.enable_controller_timing else 0

        setup_started = perf_counter_ns() if self.policy.enable_controller_timing else 0
        if self.is_setup_framework:
            if self.setup.status in {SetupStatus.FORMING, SetupStatus.ARMED}:
                self.setup.bars_alive += 1
            expiration = evaluate_setup_expiration(self.setup, timestamp, session, self.policy)
            if expiration.action == "expire_setup":
                self.setup.status = SetupStatus.EXPIRED
                self.setup.expiration_reason = expiration.reason
                setup_transition = f"{previous_setup.value}->expired"
                policy_allowed, reason_code, reason = expiration.allowed, expiration.reason_code, expiration.reason
                if self.position.status is PositionStatus.FLAT and self.policy.cooldown_after_setup_invalidation_bars:
                    self._start_cooldown(self.policy.cooldown_after_setup_invalidation_bars, timestamp, expiration.reason)
            elif self.setup.status is SetupStatus.CONSUMED and signal not in {"buy", "sell"} and self.framework != "opening_range_breakout":
                self._clear_setup("new setup cycle")
                self.setup.status = SetupStatus.ARMED
                self.setup.setup_id = f"{self.framework}:{timestamp.isoformat()}"
                self.setup.created_timestamp = timestamp
                self.setup.armed_timestamp = timestamp
                setup_transition = "consumed->armed"
            elif self.setup.status is SetupStatus.NONE and signal not in {"buy", "sell"}:
                self.setup.status = SetupStatus.ARMED
                self.setup.setup_id = f"{self.framework}:{timestamp.isoformat()}"
                self.setup.created_timestamp = timestamp
                self.setup.armed_timestamp = timestamp
                setup_transition = "none->armed"
        setup_ns = perf_counter_ns() - setup_started if self.policy.enable_controller_timing else 0

        position_started = perf_counter_ns() if self.policy.enable_controller_timing else 0
        self.position.bars_in_state += 1
        if self.position.status in {PositionStatus.LONG_ACTIVE, PositionStatus.SHORT_ACTIVE}:
            self.position.bars_since_entry_signal += 1
        if self.position.status is PositionStatus.COOLDOWN:
            if self.position.cooldown_bars_remaining <= 0:
                self.position.status = PositionStatus.FLAT
                transition = "cooldown->flat"
            else:
                self.position.cooldown_bars_remaining -= 1
        max_hold = evaluate_max_hold(self.position, timestamp, self.policy)
        if max_hold.action == "request_exit":
            max_hold_reached = True
            transition = self._exit(timestamp, max_hold.reason)
            reason_code, reason, policy_allowed = max_hold.reason_code, max_hold.reason, False
        elif signal in {"exit_long", "exit_short"}:
            valid_exit = (self.position.status in {PositionStatus.LONG_ACTIVE, PositionStatus.EXIT_PENDING} and self.position.direction == "long" and signal == "exit_long") or (self.position.status in {PositionStatus.SHORT_ACTIVE, PositionStatus.EXIT_PENDING} and self.position.direction == "short" and signal == "exit_short")
            if valid_exit:
                transition = self._exit(timestamp, decision.exit_reason or "Framework exit proposal.")
                reason_code, reason = PolicyReasonCode.ALLOWED, "Framework exit proposal accepted."
                self.event_reset = True
        elif signal in {"buy", "sell"} and not max_hold_reached and not (self.is_setup_framework and self.setup.status in {SetupStatus.EXPIRED, SetupStatus.INVALIDATED, SetupStatus.CONSUMED} and self.position.status is PositionStatus.FLAT):
            entry = evaluate_entry(self.position, signal, self.policy)
            if self.is_event_framework and self.position.status is PositionStatus.FLAT and self.last_event_side == signal and not self.event_reset:
                entry = replace(entry, allowed=False, reason_code=PolicyReasonCode.EVENT_ALREADY_CONSUMED, reason="The same event state was already consumed.", action="none")
            if entry.action == "request_exit":
                opposite_action = "request_exit"
                if self.position.status is not PositionStatus.EXIT_PENDING:
                    self.position.exit_request_timestamp = timestamp
                    self.position.status = PositionStatus.EXIT_PENDING
                    transition = f"{previous_position.value}->exit_pending"
                else:
                    transition = "repeated_exit_request_suppressed"
            elif entry.action == "reverse" and entry.allowed:
                opposite_action = "reverse"
                transition = self._enter(signal, decision, timestamp)
            elif entry.allowed and (self.position.status is PositionStatus.FLAT or self.allow_repeated):
                transition = self._enter(signal, decision, timestamp)
            else:
                transition = entry.reason_code.value.lower()
            policy_allowed, reason_code, reason = entry.allowed, entry.reason_code, entry.reason
            if entry.allowed:
                self.last_event_side = signal
                self.event_reset = False
                if self.is_setup_framework:
                    self.setup.status = SetupStatus.CONSUMED
                    self.setup.setup_id = self.setup.setup_id or f"{self.framework}:{timestamp.isoformat()}"
                    self.setup.trigger_timestamp = timestamp
                    self.setup.consumed_timestamp = timestamp
                    self.setup.trigger_count += 1
                    setup_transition = f"{previous_setup.value}->consumed"
        elif signal not in {"buy", "sell"}:
            self.event_reset = True
        position_ns = perf_counter_ns() - position_started if self.policy.enable_controller_timing else 0

        serialization_started = perf_counter_ns() if self.policy.enable_controller_timing else 0
        self.position.transition_reason = transition
        session_output = dict(session)
        session_output.pop("entry_allowed", None)
        output = {
            "research_position_state": self.position.status.value,
            "previous_position_state": previous_position.value,
            "position_transition": transition,
            "bars_in_position_state": self.position.bars_in_state,
            "setup_state": self.setup.status.value,
            "previous_setup_state": previous_setup.value,
            "setup_id": self.setup.setup_id,
            "setup_age": self.setup.bars_alive,
            "setup_transition": setup_transition,
            **session_output,
            "state_warning": "",
            "state_valid": True,
            "policy_allowed": bool(policy_allowed),
            "policy_reason_code": reason_code.value,
            "policy_reason": reason,
            "setup_expiration_reason": self.setup.expiration_reason,
            "setup_invalidation_reason": self.setup.invalidation_reason,
            "opposite_signal_action": opposite_action,
            "cooldown_active": self.position.status is PositionStatus.COOLDOWN,
            "cooldown_bars_remaining": self.position.cooldown_bars_remaining,
            "max_hold_reached": max_hold_reached,
            "session_rollover": session_rollover,
            "session_cleanup_actions": cleanup_actions,
            "level_id": None,
            "level_state": None,
            "level_test_count": 0,
            "level_retest_allowed": True,
        }
        serialization_ns = perf_counter_ns() - serialization_started if self.policy.enable_controller_timing else 0
        total_ns = perf_counter_ns() - total_started if self.policy.enable_controller_timing else 0
        self.last_timing = PolicyTimingSummary(
            generic_policy_time_ns=setup_ns + position_ns + session_ns,
            setup_policy_time_ns=setup_ns,
            position_policy_time_ns=position_ns,
            session_policy_time_ns=session_ns,
            transition_application_time_ns=position_ns,
            state_serialization_time_ns=serialization_ns,
            total_controller_time_ns=total_ns,
        )
        timing_values = (
            self.last_timing.framework_decision_time_ns,
            self.last_timing.generic_policy_time_ns,
            self.last_timing.setup_policy_time_ns,
            self.last_timing.position_policy_time_ns,
            self.last_timing.session_policy_time_ns,
            self.last_timing.level_policy_time_ns,
            self.last_timing.transition_application_time_ns,
            self.last_timing.state_serialization_time_ns,
            self.last_timing.total_controller_time_ns,
        )
        for key, value in zip(self.timing_totals, timing_values):
            self.timing_totals[key] += value
        output["controller_time_ns"] = total_ns
        output["policy_time_ns"] = setup_ns + position_ns + session_ns
        should_snapshot = self.snapshot_mode is SnapshotMode.FULL or (
            self.snapshot_mode is SnapshotMode.TRANSITIONS_ONLY
            and (transition != "none" or setup_transition != "none" or session_rollover)
        )
        if should_snapshot:
            self.stored_snapshots.append(self.snapshot(timestamp, dict(session)).to_dict())
        return output

    def final_summary(self) -> dict[str, Any]:
        timestamp = self.position.activation_timestamp or pd.Timestamp("1970-01-01", tz="UTC")
        value = self.snapshot(timestamp).to_dict()
        value["policy_configuration"] = self.policy.to_dict()
        value["controller_timing"] = dict(self.timing_totals)
        value["snapshot_mode"] = self.snapshot_mode.value
        value["stored_snapshot_count"] = len(self.stored_snapshots) + (1 if self.snapshot_mode is SnapshotMode.FINAL_ONLY else 0)
        value["continuity"] = {
            "previous_session_id": self.previous_session_id,
            "last_event_side": self.last_event_side,
            "event_reset": self.event_reset,
        }
        return value
