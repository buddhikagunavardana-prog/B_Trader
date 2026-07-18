from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PolicySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class PolicyReasonCode(str, Enum):
    ALLOWED = "ALLOWED"
    NO_ACTION = "NO_ACTION"
    SETUP_EXPIRED = "SETUP_EXPIRED"
    SETUP_INVALIDATED = "SETUP_INVALIDATED"
    SETUP_ALREADY_CONSUMED = "SETUP_ALREADY_CONSUMED"
    SESSION_ROLLOVER_RESET = "SESSION_ROLLOVER_RESET"
    SESSION_ENTRY_CUTOFF_REACHED = "SESSION_ENTRY_CUTOFF_REACHED"
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    MAX_HOLD_REACHED = "MAX_HOLD_REACHED"
    REPEATED_ENTRY_SUPPRESSED = "REPEATED_ENTRY_SUPPRESSED"
    OPPOSITE_SIGNAL_IGNORED = "OPPOSITE_SIGNAL_IGNORED"
    OPPOSITE_SIGNAL_REJECTED = "OPPOSITE_SIGNAL_REJECTED"
    EXIT_REQUIRED_BEFORE_REVERSAL = "EXIT_REQUIRED_BEFORE_REVERSAL"
    IMMEDIATE_REVERSAL_ALLOWED = "IMMEDIATE_REVERSAL_ALLOWED"
    LEVEL_ALREADY_TESTED = "LEVEL_ALREADY_TESTED"
    LEVEL_INVALIDATED = "LEVEL_INVALIDATED"
    LEVEL_RETEST_COOLDOWN = "LEVEL_RETEST_COOLDOWN"
    MISSING_REQUIRED_SETUP = "MISSING_REQUIRED_SETUP"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    EVENT_ALREADY_CONSUMED = "EVENT_ALREADY_CONSUMED"


class OppositeSignalMode(str, Enum):
    IGNORE = "ignore"
    REJECT = "reject"
    REQUEST_EXIT = "request_exit"
    EXIT_THEN_REVERSE = "exit_then_reverse"
    ALLOW_IMMEDIATE_REVERSE = "allow_immediate_reverse"


class NestedInsideBarPolicy(str, Enum):
    KEEP_ORIGINAL_MOTHER_BAR = "keep_original_mother_bar"
    REPLACE_WITH_LATEST_MOTHER_BAR = "replace_with_latest_mother_bar"
    NARROW_RANGE = "narrow_range"
    REJECT_NESTED_SETUP = "reject_nested_setup"


class LevelState(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    TESTING = "testing"
    BOUNCED = "bounced"
    BROKEN = "broken"
    INVALIDATED = "invalidated"
    RETIRED = "retired"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: PolicyReasonCode
    reason: str
    action: str = "none"
    severity: PolicySeverity = PolicySeverity.INFO
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reason_code"] = self.reason_code.value
        value["severity"] = self.severity.value
        return value


@dataclass(frozen=True)
class PolicyTimingSummary:
    framework_decision_time_ns: int = 0
    generic_policy_time_ns: int = 0
    setup_policy_time_ns: int = 0
    position_policy_time_ns: int = 0
    session_policy_time_ns: int = 0
    level_policy_time_ns: int = 0
    transition_application_time_ns: int = 0
    state_serialization_time_ns: int = 0
    total_controller_time_ns: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class LevelRecord:
    level_id: str
    level_type: str
    source_timestamp: Any
    confirmation_timestamp: Any
    price: float
    tolerance: float
    state: LevelState = LevelState.CONFIRMED
    age: int = 0
    test_count: int = 0
    successful_bounce_count: int = 0
    break_count: int = 0
    last_test_bar: int | None = None
    last_test_timestamp: Any = None
    last_outcome: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyConfiguration:
    setup_expiration_mode: str = "bars"
    setup_expiration_bars: int = 5
    expire_at_session_end: bool = True
    expire_at_entry_cutoff: bool = False
    cooldown_after_exit_bars: int = 0
    cooldown_after_setup_invalidation_bars: int = 0
    cooldown_after_setup_consumption_bars: int = 0
    max_hold_enforcement: bool = False
    max_hold_bars: int | None = None
    max_hold_duration: str | None = None
    opposite_signal_mode: OppositeSignalMode = OppositeSignalMode.REQUEST_EXIT
    clear_untriggered_setups_on_rollover: bool = True
    clear_consumed_setups_on_rollover: bool = True
    clear_cooldown_on_rollover: bool = False
    request_exit_at_session_close: bool = False
    carry_active_position_across_sessions: bool = True
    carry_levels_across_sessions: bool = False
    level_retest_cooldown_bars: int = 1
    level_max_age_bars: int = 500
    allow_level_role_reversal: bool = False
    nested_inside_bar_policy: NestedInsideBarPolicy = NestedInsideBarPolicy.KEEP_ORIGINAL_MOTHER_BAR
    minimum_squeeze_bars: int = 1
    maximum_release_to_trigger_bars: int = 5
    enable_controller_timing: bool = False

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None = None) -> "PolicyConfiguration":
        data = dict(values or {})
        if "opposite_signal_mode" in data:
            data["opposite_signal_mode"] = OppositeSignalMode(data["opposite_signal_mode"])
        if "nested_inside_bar_policy" in data:
            data["nested_inside_bar_policy"] = NestedInsideBarPolicy(data["nested_inside_bar_policy"])
        known = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["opposite_signal_mode"] = self.opposite_signal_mode.value
        value["nested_inside_bar_policy"] = self.nested_inside_bar_policy.value
        return value
