from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.research.run_management.run_identity import stable_identity_hash


CAMPAIGN_MANIFEST_VERSION = "1.0"
CAMPAIGN_PLAN_VERSION = "1.0"
CAMPAIGN_AGGREGATE_VERSION = "1.0"


def _safe_name(value: str, field_name: str) -> str:
    candidate = str(value).strip()
    if not candidate or any(part in candidate for part in ("..", "/", "\\")):
        raise ValueError(f"{field_name} must be a safe local name")
    return candidate


def _timestamp(value: Any) -> pd.Timestamp | None:
    return None if value in (None, "") else pd.Timestamp(value)


class CampaignStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RECOVERABLE = "recoverable"
    INVALID = "invalid"


class CampaignTaskStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RECOVERABLE = "recoverable"
    INVALID = "invalid"
    SKIPPED = "skipped"
    REUSED = "reused"


class CampaignFailurePolicy(str, Enum):
    FAIL_FAST = "fail_fast"
    CONTINUE = "continue"


@dataclass(frozen=True)
class HistoricalResearchRange:
    name: str
    start_timestamp: pd.Timestamp | None = None
    end_timestamp: pd.Timestamp | None = None
    start_row: int | None = None
    end_row: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _safe_name(self.name, "research range name"))
        object.__setattr__(self, "start_timestamp", _timestamp(self.start_timestamp))
        object.__setattr__(self, "end_timestamp", _timestamp(self.end_timestamp))
        timestamp_mode = self.start_timestamp is not None or self.end_timestamp is not None
        row_mode = self.start_row is not None or self.end_row is not None
        if timestamp_mode and row_mode:
            raise ValueError("research range cannot mix row and timestamp bounds")
        if self.start_timestamp is not None and self.end_timestamp is not None and self.start_timestamp > self.end_timestamp:
            raise ValueError("research range start_timestamp must not exceed end_timestamp")
        if self.start_row is not None and self.start_row < 0:
            raise ValueError("research range start_row must be non-negative")
        if self.end_row is not None and self.end_row < 1:
            raise ValueError("research range end_row must be positive")
        if self.start_row is not None and self.end_row is not None and self.start_row >= self.end_row:
            raise ValueError("research range end_row must be greater than start_row")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_timestamp": None if self.start_timestamp is None else self.start_timestamp.isoformat(),
            "end_timestamp": None if self.end_timestamp is None else self.end_timestamp.isoformat(),
            "start_row": self.start_row,
            "end_row": self.end_row,
        }


@dataclass(frozen=True)
class HistoricalSourceSetBinding:
    name: str
    execution_timeframe: str
    role_timeframes: Mapping[str, str]
    sources: Mapping[str, Any] = field(repr=False, compare=False)
    completed_bar_alignment: bool = True
    applicable_frameworks: tuple[str, ...] = ("*",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _safe_name(self.name, "source-set name"))
        object.__setattr__(self, "role_timeframes", dict(self.role_timeframes))
        object.__setattr__(self, "sources", dict(self.sources))
        object.__setattr__(self, "applicable_frameworks", tuple(self.applicable_frameworks))
        if not self.execution_timeframe:
            raise ValueError("source-set execution_timeframe is required")
        if not self.role_timeframes or not self.sources:
            raise ValueError("source-set roles and sources must not be empty")
        if set(self.role_timeframes) != set(self.sources):
            raise ValueError("source-set roles must exactly match source roles")
        if self.execution_timeframe not in self.role_timeframes.values():
            raise ValueError("source-set execution_timeframe must be present in role_timeframes")
        if not self.completed_bar_alignment:
            raise ValueError("historical campaign source sets require completed-bar alignment")
        if not self.applicable_frameworks:
            raise ValueError("source-set applicable_frameworks must not be empty")

    def descriptor_snapshot(self) -> dict[str, Any]:
        descriptors: dict[str, Any] = {}
        for role in sorted(self.sources):
            source = self.sources[role]
            source.validate()
            descriptor = dict(source.descriptor())
            descriptors[role] = {
                "source_type": descriptor.get("source_type"),
                "row_count": int(source.row_count()),
                "schema": list(source.schema()),
                "schema_fingerprint": stable_identity_hash({"columns": list(source.schema())}),
                "index_name": descriptor.get("index_name"),
                "index_start": None if source.row_count() == 0 else str(source.index()[0]),
                "index_end": None if source.row_count() == 0 else str(source.index()[-1]),
                "fingerprint": source.fingerprint(),
                "timeframe": self.role_timeframes[role],
            }
        return descriptors

    def identity_snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "execution_timeframe": self.execution_timeframe,
            "role_timeframes": dict(sorted(self.role_timeframes.items())),
            "completed_bar_alignment": self.completed_bar_alignment,
            "applicable_frameworks": list(self.applicable_frameworks),
            "sources": self.descriptor_snapshot(),
        }

    @property
    def fingerprint(self) -> str:
        return stable_identity_hash(self.identity_snapshot())


@dataclass(frozen=True)
class HistoricalCampaignConfig:
    campaign_name: str
    framework_configuration_names: tuple[str, ...]
    source_set_names: tuple[str, ...]
    research_ranges: tuple[HistoricalResearchRange, ...]
    chunk_size_rows: int = 1_000
    warmup_rows: int = 0
    warmup_safety_margin: int = 5
    overlap_policy: str = "dependency_aware"
    diagnostic_level: str = "standard"
    snapshot_mode: str = "none"
    output_root: str = "reports/historical_campaigns"
    failure_policy: CampaignFailurePolicy = CampaignFailurePolicy.FAIL_FAST
    cancellation_behavior: str = "stop_between_tasks"
    structural_aggregation: Mapping[str, Any] = field(default_factory=lambda: {"enabled": True})
    concurrency: int = 1
    artifact_format: str = "csv"
    compression: str | None = "gzip"
    maximum_memory_bytes: int = 256_000_000
    maximum_output_rows_per_artifact: int = 100_000
    strict_integrity_mode: bool = True
    manifest_schema_version: str = CAMPAIGN_MANIFEST_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "campaign_name", _safe_name(self.campaign_name, "campaign name"))
        object.__setattr__(self, "framework_configuration_names", tuple(self.framework_configuration_names))
        object.__setattr__(self, "source_set_names", tuple(self.source_set_names))
        object.__setattr__(self, "research_ranges", tuple(self.research_ranges))
        object.__setattr__(self, "structural_aggregation", dict(self.structural_aggregation))
        if isinstance(self.failure_policy, str):
            object.__setattr__(self, "failure_policy", CampaignFailurePolicy(self.failure_policy))
        if self.manifest_schema_version != CAMPAIGN_MANIFEST_VERSION:
            raise ValueError(f"unsupported campaign manifest schema version: {self.manifest_schema_version}")
        if not self.framework_configuration_names:
            raise ValueError("campaign framework selection must not be empty")
        if not self.source_set_names:
            raise ValueError("campaign source-set selection must not be empty")
        if not self.research_ranges:
            raise ValueError("campaign research ranges must not be empty")
        if len(set(self.source_set_names)) != len(self.source_set_names):
            raise ValueError("campaign source-set selection contains duplicates")
        for name in self.source_set_names:
            _safe_name(name, "source-set selection")
        if self.concurrency != 1:
            raise ValueError("Phase 24.9 campaign concurrency must be exactly 1")
        if self.chunk_size_rows < 1 or self.warmup_rows < 0 or self.warmup_safety_margin < 0:
            raise ValueError("campaign chunk and warm-up settings are invalid")
        if self.overlap_policy not in {"none", "fixed_rows", "dependency_aware"}:
            raise ValueError("unsupported campaign overlap policy")
        if self.diagnostic_level not in {"none", "summary", "standard", "full"}:
            raise ValueError("unsupported campaign diagnostic level")
        if self.snapshot_mode not in {"none", "final_only", "transitions_only", "full"}:
            raise ValueError("unsupported campaign snapshot mode")
        if self.cancellation_behavior not in {"stop_between_tasks", "pause_between_tasks"}:
            raise ValueError("unsupported campaign cancellation behavior")
        if self.artifact_format not in {"csv", "parquet"}:
            raise ValueError("campaign artifact_format must be csv or parquet")
        if self.compression not in {None, "gzip"}:
            raise ValueError("campaign compression must be null or gzip")
        if self.maximum_memory_bytes < 1 or self.maximum_output_rows_per_artifact < 1:
            raise ValueError("campaign memory and artifact limits must be positive")

    def identity_snapshot(self) -> dict[str, Any]:
        return {
            "campaign_name": self.campaign_name,
            "framework_configuration_names": list(self.framework_configuration_names),
            "source_set_names": list(self.source_set_names),
            "research_ranges": [item.to_dict() for item in self.research_ranges],
            "chunk_size_rows": self.chunk_size_rows,
            "warmup_rows": self.warmup_rows,
            "warmup_safety_margin": self.warmup_safety_margin,
            "overlap_policy": self.overlap_policy,
            "diagnostic_level": self.diagnostic_level,
            "snapshot_mode": self.snapshot_mode,
            "failure_policy": self.failure_policy.value,
            "cancellation_behavior": self.cancellation_behavior,
            "structural_aggregation": dict(sorted(self.structural_aggregation.items())),
            "concurrency": self.concurrency,
            "artifact_format": self.artifact_format,
            "compression": self.compression,
            "maximum_memory_bytes": self.maximum_memory_bytes,
            "maximum_output_rows_per_artifact": self.maximum_output_rows_per_artifact,
            "strict_integrity_mode": self.strict_integrity_mode,
            "manifest_schema_version": self.manifest_schema_version,
        }


@dataclass(frozen=True)
class HistoricalCampaignTask:
    task_id: str
    framework_name: str
    framework_version: str
    framework_configuration: Mapping[str, Any]
    framework_configuration_fingerprint: str
    source_set_name: str
    source_set_fingerprint: str
    source_fingerprints: Mapping[str, str]
    source_schema_fingerprints: Mapping[str, str]
    research_range: HistoricalResearchRange
    child_configuration: Mapping[str, Any]
    child_configuration_fingerprint: str
    child_run_id: str
    child_chunk_count: int
    child_execution_row_count: int
    reason: str
    status: CampaignTaskStatus = CampaignTaskStatus.PLANNED

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["research_range"] = self.research_range.to_dict()
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class HistoricalCampaignPlan:
    campaign_id: str
    configuration_fingerprint: str
    code_fingerprint: str
    plan_fingerprint: str
    source_set_fingerprints: Mapping[str, str]
    tasks: tuple[HistoricalCampaignTask, ...]
    config: HistoricalCampaignConfig = field(repr=False, compare=False)
    plan_version: str = CAMPAIGN_PLAN_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "configuration": self.config.identity_snapshot(),
            "configuration_fingerprint": self.configuration_fingerprint,
            "code_fingerprint": self.code_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "source_set_fingerprints": dict(self.source_set_fingerprints),
            "task_ordering": [task.task_id for task in self.tasks],
            "tasks": [task.to_dict() for task in self.tasks],
            "plan_version": self.plan_version,
        }


@dataclass(frozen=True)
class HistoricalCampaignTaskResult:
    task_id: str
    child_run_id: str
    status: CampaignTaskStatus
    attempt_number: int
    child_run_directory: str
    child_integrity_fingerprint: str
    child_schema_fingerprint: str
    logical_row_count: int
    chunk_count: int
    valid_row_count: int
    skipped_row_count: int
    decision_direction_counts: Mapping[str, int] = field(default_factory=dict)
    lifecycle_state_counts: Mapping[str, int] = field(default_factory=dict)
    warning_count: int = 0
    validation_count: int = 0
    memory_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    timing_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HistoricalCampaignTaskResult":
        data = dict(value)
        data["status"] = CampaignTaskStatus(data["status"])
        data["errors"] = tuple(data.get("errors", ()))
        return cls(**data)


@dataclass(frozen=True)
class HistoricalCampaignAggregate:
    campaign_id: str
    task_count: int
    completed_task_count: int
    reused_task_count: int
    logical_row_count: int
    chunk_count: int
    valid_row_count: int
    skipped_row_count: int
    task_rows: tuple[Mapping[str, Any], ...]
    aggregate_fingerprint: str
    aggregate_version: str = CAMPAIGN_AGGREGATE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalCampaignManifest:
    campaign_id: str
    status: CampaignStatus
    configuration_fingerprint: str
    code_fingerprint: str
    plan_fingerprint: str
    task_ordering: tuple[str, ...]
    source_set_fingerprints: Mapping[str, str]
    task_statuses: Mapping[str, str]
    task_attempts: Mapping[str, int]
    task_results: Mapping[str, Mapping[str, Any]]
    child_run_ids: Mapping[str, str]
    child_integrity_fingerprints: Mapping[str, str]
    aggregate_version: str = CAMPAIGN_AGGREGATE_VERSION
    aggregate_fingerprint: str = ""
    warnings: tuple[str, ...] = ()
    structural_counts: Mapping[str, int] = field(default_factory=dict)
    cancellation_state: str = "active"
    recovery_state: str = "clean"
    timing_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    memory_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    manifest_schema_version: str = CAMPAIGN_MANIFEST_VERSION

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class HistoricalCampaignResult:
    campaign_id: str
    status: CampaignStatus
    campaign_directory: str
    completed_tasks: int
    total_tasks: int
    reused_tasks: int
    aggregate: HistoricalCampaignAggregate | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignRecoveryReport:
    campaign_id: str
    retained_tasks: tuple[str, ...]
    reused_tasks: tuple[str, ...]
    resumed_tasks: tuple[str, ...]
    invalidated_tasks: tuple[str, ...]
    tasks_to_rerun: tuple[str, ...]
    orphan_files: tuple[str, ...]
    corrupt_files: tuple[str, ...]
    incompatible_files: tuple[str, ...]
    stale_summaries: tuple[str, ...]
    retained_child_runs: tuple[str, ...]


def safe_campaign_directory(root: str | Path, campaign_id: str) -> Path:
    _safe_name(campaign_id, "campaign ID")
    base = Path(root).resolve()
    target = (base / campaign_id).resolve()
    if base not in target.parents:
        raise ValueError("campaign path escapes output root")
    return target
