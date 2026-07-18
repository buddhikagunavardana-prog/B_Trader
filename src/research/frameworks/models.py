from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

import pandas as pd

from src.research.run_management.run_identity import stable_identity_hash


class PreparationMode(str, Enum):
    PRECOMPUTED_ONLY = "precomputed_only"
    COMPUTE_MISSING = "compute_missing"


class OutputMode(str, Enum):
    DATAFRAME = "dataframe"
    RECORDS = "records"


@dataclass(frozen=True)
class FrameworkResearchConfiguration:
    framework: str
    framework_version: str
    parameters: Mapping[str, Any]
    symbol: str
    market_type: str
    timeframe_roles: Mapping[str, str]
    primary_role: str
    start_timestamp: pd.Timestamp | None = None
    end_timestamp: pd.Timestamp | None = None
    warmup_policy: str = "skip"
    output_mode: OutputMode = OutputMode.DATAFRAME
    include_diagnostics: bool = True
    include_warnings: bool = True
    allow_experimental: bool = False
    preparation_mode: PreparationMode = PreparationMode.PRECOMPUTED_ONLY
    random_seed: int = 0
    configuration_version: str = "1.0"
    run_id: str | None = None
    enable_stateful_research: bool = True
    position_transition_policy: str = "conservative"
    reverse_on_opposite_signal: bool = False
    cooldown_bars: int = 0
    allow_repeated_entries: bool = False
    setup_expiration_defaults: Mapping[str, int] = field(default_factory=dict)
    session_configuration: Mapping[str, Any] = field(default_factory=dict)
    state_diagnostics_level: str = "standard"
    persist_state_snapshots: bool = False
    setup_expiration_mode: str = "bars"
    setup_expiration_bars: int = 5
    expire_at_session_end: bool = True
    expire_at_entry_cutoff: bool = False
    opposite_signal_mode: str = "request_exit"
    cooldown_after_exit_bars: int = 0
    cooldown_after_setup_invalidation_bars: int = 0
    cooldown_after_setup_consumption_bars: int = 0
    max_hold_enforcement: bool = False
    max_hold_bars: int | None = None
    max_hold_duration: str | None = None
    request_exit_at_session_close: bool = False
    clear_cooldown_on_rollover: bool = False
    clear_untriggered_setups_on_rollover: bool = True
    clear_consumed_setups_on_rollover: bool = True
    carry_active_position_across_sessions: bool = True
    carry_levels_across_sessions: bool = False
    level_retest_cooldown_bars: int = 1
    level_max_age_bars: int = 500
    allow_level_role_reversal: bool = False
    nested_inside_bar_policy: str = "keep_original_mother_bar"
    minimum_squeeze_bars: int = 1
    maximum_release_to_trigger_bars: int = 5
    enable_controller_timing: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", dict(self.parameters))
        object.__setattr__(self, "timeframe_roles", dict(self.timeframe_roles))
        object.__setattr__(self, "setup_expiration_defaults", dict(self.setup_expiration_defaults))
        object.__setattr__(self, "session_configuration", dict(self.session_configuration))
        if self.start_timestamp is not None:
            object.__setattr__(self, "start_timestamp", pd.Timestamp(self.start_timestamp))
        if self.end_timestamp is not None:
            object.__setattr__(self, "end_timestamp", pd.Timestamp(self.end_timestamp))
        if isinstance(self.output_mode, str):
            object.__setattr__(self, "output_mode", OutputMode(self.output_mode))
        if isinstance(self.preparation_mode, str):
            object.__setattr__(self, "preparation_mode", PreparationMode(self.preparation_mode))
        if self.run_id is None:
            payload = self.to_dict(include_run_id=False)
            object.__setattr__(self, "run_id", f"framework_{stable_identity_hash(payload)}")

    def to_dict(self, include_run_id: bool = True) -> dict[str, Any]:
        result = {
            "framework": self.framework, "framework_version": self.framework_version,
            "parameters": dict(self.parameters), "symbol": self.symbol, "market_type": self.market_type,
            "timeframe_roles": dict(self.timeframe_roles), "primary_role": self.primary_role,
            "start_timestamp": None if self.start_timestamp is None else self.start_timestamp.isoformat(),
            "end_timestamp": None if self.end_timestamp is None else self.end_timestamp.isoformat(),
            "warmup_policy": self.warmup_policy, "output_mode": self.output_mode.value,
            "include_diagnostics": self.include_diagnostics, "include_warnings": self.include_warnings,
            "allow_experimental": self.allow_experimental, "preparation_mode": self.preparation_mode.value,
            "random_seed": self.random_seed, "configuration_version": self.configuration_version,
            "enable_stateful_research": self.enable_stateful_research,
            "position_transition_policy": self.position_transition_policy,
            "reverse_on_opposite_signal": self.reverse_on_opposite_signal,
            "cooldown_bars": self.cooldown_bars,"allow_repeated_entries": self.allow_repeated_entries,
            "setup_expiration_defaults":dict(self.setup_expiration_defaults),"session_configuration":dict(self.session_configuration),
            "state_diagnostics_level":self.state_diagnostics_level,"persist_state_snapshots":self.persist_state_snapshots,
            "setup_expiration_mode":self.setup_expiration_mode,"setup_expiration_bars":self.setup_expiration_bars,
            "expire_at_session_end":self.expire_at_session_end,"expire_at_entry_cutoff":self.expire_at_entry_cutoff,
            "opposite_signal_mode":self.opposite_signal_mode,
            "cooldown_after_exit_bars":self.cooldown_after_exit_bars,
            "cooldown_after_setup_invalidation_bars":self.cooldown_after_setup_invalidation_bars,
            "cooldown_after_setup_consumption_bars":self.cooldown_after_setup_consumption_bars,
            "max_hold_enforcement":self.max_hold_enforcement,"max_hold_bars":self.max_hold_bars,
            "max_hold_duration":self.max_hold_duration,"request_exit_at_session_close":self.request_exit_at_session_close,
            "clear_cooldown_on_rollover":self.clear_cooldown_on_rollover,
            "clear_untriggered_setups_on_rollover":self.clear_untriggered_setups_on_rollover,
            "clear_consumed_setups_on_rollover":self.clear_consumed_setups_on_rollover,
            "carry_active_position_across_sessions":self.carry_active_position_across_sessions,
            "carry_levels_across_sessions":self.carry_levels_across_sessions,
            "level_retest_cooldown_bars":self.level_retest_cooldown_bars,"level_max_age_bars":self.level_max_age_bars,
            "allow_level_role_reversal":self.allow_level_role_reversal,
            "nested_inside_bar_policy":self.nested_inside_bar_policy,
            "minimum_squeeze_bars":self.minimum_squeeze_bars,
            "maximum_release_to_trigger_bars":self.maximum_release_to_trigger_bars,
            "enable_controller_timing":self.enable_controller_timing,
        }
        if include_run_id:
            result["run_id"] = self.run_id
        return result


@dataclass(frozen=True)
class PreparedTimeframeData:
    role: str
    timeframe: str
    frame: pd.DataFrame
    precomputed_indicator_columns: tuple[str, ...]
    first_valid_timestamp: pd.Timestamp | None
    last_valid_timestamp: pd.Timestamp | None
    row_count: int
    warmup_rows: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role, "timeframe": self.timeframe,
            "columns": list(self.frame.columns),
            "precomputed_indicator_columns": list(self.precomputed_indicator_columns),
            "first_valid_timestamp": None if self.first_valid_timestamp is None else self.first_valid_timestamp.isoformat(),
            "last_valid_timestamp": None if self.last_valid_timestamp is None else self.last_valid_timestamp.isoformat(),
            "row_count": self.row_count, "warmup_rows": self.warmup_rows,
            "metadata": dict(self.metadata), "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class AlignmentDiagnostic:
    role: str
    decision_timestamp: pd.Timestamp
    source_timestamp: pd.Timestamp | None
    completed_bar: bool
    missing_role: bool
    stale_age_seconds: float | None
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role, "source_timestamp": None if self.source_timestamp is None else self.source_timestamp.isoformat(),
            "completed_bar": self.completed_bar, "missing_role": self.missing_role,
            "stale_age_seconds": self.stale_age_seconds, "alignment_warning": self.warning,
        }


@dataclass(frozen=True)
class ResearchValidationIssue:
    code: str
    severity: str
    message: str
    timestamp: str | None = None


@dataclass(frozen=True)
class ResearchValidationResult:
    issues: tuple[ResearchValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "issues": [asdict(item) for item in self.issues]}


@dataclass(frozen=True)
class DecisionSeriesRow:
    timestamp: pd.Timestamp
    framework: str
    framework_version: str
    signal: str
    direction: str
    entry_allowed: bool
    exit_requested: bool
    confidence: float
    entry_reason: str
    exit_reason: str
    stop_type: str
    stop_value: float | None
    stop_distance: float | None
    target_type: str
    target_value: float | None
    reward_to_risk: float | None
    trailing_stop_type: str
    risk_fraction_suggestion: float | None
    maximum_holding_period: int | None
    diagnostics: Mapping[str, Any]
    warnings: tuple[str, ...]
    rows_available: Mapping[str, int]
    input_availability_flags: Mapping[str, bool]
    warmup_complete: bool
    decision_valid: bool
    skip_reason: str

    def to_record(self) -> dict[str, Any]:
        import json
        return {
            "timestamp": pd.Timestamp(self.timestamp), "framework": self.framework,
            "framework_version": self.framework_version, "signal": self.signal, "direction": self.direction,
            "entry_allowed": self.entry_allowed, "exit_requested": self.exit_requested,
            "confidence": float(self.confidence), "entry_reason": self.entry_reason, "exit_reason": self.exit_reason,
            "stop_type": self.stop_type, "stop_value": self.stop_value, "stop_distance": self.stop_distance,
            "target_type": self.target_type, "target_value": self.target_value, "reward_to_risk": self.reward_to_risk,
            "trailing_stop_type": self.trailing_stop_type, "risk_fraction_suggestion": self.risk_fraction_suggestion,
            "maximum_holding_period": self.maximum_holding_period,
            "diagnostics": json.dumps(dict(self.diagnostics), sort_keys=True, separators=(",", ":"), default=str),
            "warnings": json.dumps(list(self.warnings), sort_keys=True, separators=(",", ":"), default=str),
            "rows_available": json.dumps(dict(self.rows_available), sort_keys=True, separators=(",", ":")),
            "warmup_complete": self.warmup_complete, "decision_valid": self.decision_valid,
            "skip_reason": self.skip_reason,
        }


@dataclass(frozen=True)
class DecisionSeriesResult:
    configuration: FrameworkResearchConfiguration
    framework_metadata: Mapping[str, Any]
    decisions: pd.DataFrame
    summary: Mapping[str, Any]
    validation: ResearchValidationResult
    warnings: tuple[str, ...]
    execution_duration_seconds: float
    rows_evaluated: int
    rows_skipped: int
    first_decision_timestamp: pd.Timestamp | None
    last_decision_timestamp: pd.Timestamp | None
    reproducibility: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        records = self.decisions.copy()
        if "timestamp" in records:
            records["timestamp"] = records["timestamp"].map(lambda value: value.isoformat())
        return {
            "configuration": self.configuration.to_dict(), "framework_metadata": dict(self.framework_metadata),
            "decisions": records.to_dict(orient="records"), "summary": dict(self.summary),
            "validation": self.validation.to_dict(), "warnings": list(self.warnings),
            "execution_duration_seconds": self.execution_duration_seconds,
            "rows_evaluated": self.rows_evaluated, "rows_skipped": self.rows_skipped,
            "first_decision_timestamp": None if self.first_decision_timestamp is None else self.first_decision_timestamp.isoformat(),
            "last_decision_timestamp": None if self.last_decision_timestamp is None else self.last_decision_timestamp.isoformat(),
            "reproducibility": dict(self.reproducibility),
        }
