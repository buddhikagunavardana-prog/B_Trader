from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DiagnosticLevel(str, Enum):
    NONE = "none"
    SUMMARY = "summary"
    STANDARD = "standard"
    FULL = "full"


class SnapshotMode(str, Enum):
    NONE = "none"
    FINAL_ONLY = "final_only"
    TRANSITIONS_ONLY = "transitions_only"
    FULL = "full"


class ExecutionMode(str, Enum):
    STATELESS = "stateless"
    STATEFUL = "stateful"
    STATEFUL_POLICY = "stateful_policy"
    STATEFUL_POLICY_INSTRUMENTED = "stateful_policy_instrumented"


@dataclass(frozen=True)
class ProfileMeasurement:
    framework: str
    category: str
    row_count: int
    mode: str
    instrumentation_enabled: bool
    warmup_runs: int
    measured_runs: int
    mean_ms: float
    median_ms: float
    minimum_ms: float
    maximum_ms: float
    standard_deviation_ms: float
    p90_ms: float
    preparation_ms: float = 0.0
    alignment_ms: float = 0.0
    decision_ms: float = 0.0
    controller_ms: float = 0.0
    policy_ms: float = 0.0
    session_ms: float = 0.0
    setup_ms: float = 0.0
    position_ms: float = 0.0
    diagnostics_ms: float = 0.0
    normalization_ms: float = 0.0
    serialization_ms: float = 0.0
    manifest_ms: float = 0.0
    memory_bytes: int = 0
    repeated_indicator_calculations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PerformanceBudget:
    maximum_instrumentation_overhead_percent: float = 10.0
    instrumentation_warning_percent: float = 3.0
    instrumentation_hard_warning_percent: float = 5.0
    maximum_repeated_indicator_calculations: int = 0
    maximum_scaling_ratio: float = 12.0
    memory_growth_warning_ratio: float = 12.0
    allowed_output_variance: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
