from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.research.frameworks.models import FrameworkResearchConfiguration


class OverlapMode(str, Enum):
    NONE = "none"
    FIXED_ROWS = "fixed_rows"
    DEPENDENCY_AWARE = "dependency_aware"


class ChunkStatus(str, Enum):
    PLANNED="planned"; RUNNING="running"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"; CORRUPT="corrupt"; SKIPPED="skipped"; SUPERSEDED="superseded"


class RunStatus(str, Enum):
    PLANNED="planned"; RUNNING="running"; PAUSED="paused"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"; RECOVERABLE="recoverable"; CORRUPT="corrupt"


@dataclass(frozen=True)
class HistoricalResearchRunConfig:
    run_name: str
    framework_configuration: FrameworkResearchConfiguration
    execution_timeframe: str
    start_timestamp: pd.Timestamp | None = None
    end_timestamp: pd.Timestamp | None = None
    chunk_size_rows: int = 1_000
    warmup_rows: int = 0
    warmup_safety_margin: int = 5
    overlap_policy: OverlapMode = OverlapMode.DEPENDENCY_AWARE
    output_directory: str = "reports/research_runs"
    checkpoint_directory: str | None = None
    artifact_format: str = "csv"
    compression: str | None = "gzip"
    diagnostic_level: str = "standard"
    snapshot_mode: str = "none"
    stateful_mode: bool = True
    policy_mode: bool = True
    instrumentation_mode: bool = False
    resume_enabled: bool = True
    overwrite_policy: str = "reject"
    maximum_memory_bytes: int = 256_000_000
    maximum_output_rows_per_artifact: int = 100_000
    cancellation_check_interval: int = 1
    strict_integrity_mode: bool = True
    run_id: str | None = None

    def __post_init__(self):
        if isinstance(self.overlap_policy, str): object.__setattr__(self, "overlap_policy", OverlapMode(self.overlap_policy))
        if self.start_timestamp is not None: object.__setattr__(self, "start_timestamp", pd.Timestamp(self.start_timestamp))
        if self.end_timestamp is not None: object.__setattr__(self, "end_timestamp", pd.Timestamp(self.end_timestamp))
        if not self.run_name or any(part in self.run_name for part in ("..", "/", "\\")): raise ValueError("run_name must be a safe local name")
        if not self.execution_timeframe: raise ValueError("execution_timeframe is required")
        expected_timeframe = self.framework_configuration.timeframe_roles.get(self.framework_configuration.primary_role)
        if expected_timeframe != self.execution_timeframe: raise ValueError("execution_timeframe must match the primary framework role")
        if self.start_timestamp is not None and self.end_timestamp is not None and self.start_timestamp > self.end_timestamp: raise ValueError("start_timestamp must not be after end_timestamp")
        if self.chunk_size_rows < 1: raise ValueError("chunk_size_rows must be positive")
        if self.warmup_rows < 0 or self.warmup_safety_margin < 0: raise ValueError("warm-up rows must be non-negative")
        if self.maximum_memory_bytes < 1 or self.maximum_output_rows_per_artifact < 1: raise ValueError("memory and artifact row limits must be positive")
        if self.artifact_format not in {"csv", "parquet"}: raise ValueError("artifact_format must be csv or parquet")
        if self.compression not in {None, "gzip"}: raise ValueError("compression must be null or gzip")

    @property
    def symbol(self): return self.framework_configuration.symbol
    @property
    def timeframe_mappings(self): return self.framework_configuration.timeframe_roles

    def identity_snapshot(self):
        return {
            "run_name": self.run_name, "framework_configuration": self.framework_configuration.to_dict(),
            "execution_timeframe": self.execution_timeframe,
            "start_timestamp": None if self.start_timestamp is None else self.start_timestamp.isoformat(),
            "end_timestamp": None if self.end_timestamp is None else self.end_timestamp.isoformat(),
            "chunk_size_rows": self.chunk_size_rows, "warmup_rows": self.warmup_rows,
            "warmup_safety_margin": self.warmup_safety_margin, "overlap_policy": self.overlap_policy.value,
            "artifact_format": self.artifact_format, "compression": self.compression,
            "diagnostic_level": self.diagnostic_level, "snapshot_mode": self.snapshot_mode,
            "stateful_mode": self.stateful_mode, "policy_mode": self.policy_mode,
            "instrumentation_mode": self.instrumentation_mode,
            "resume_enabled": self.resume_enabled, "overwrite_policy": self.overwrite_policy,
            "maximum_memory_bytes": self.maximum_memory_bytes,
            "maximum_output_rows_per_artifact": self.maximum_output_rows_per_artifact,
            "cancellation_check_interval": self.cancellation_check_interval,
            "strict_integrity_mode": self.strict_integrity_mode,
        }


@dataclass(frozen=True)
class ChunkPlan:
    run_id: str; chunk_index: int; logical_start: int; logical_end: int; read_start: int; read_end: int
    warmup_prefix_size: int; output_start: int; output_end: int; expected_input_row_count: int
    expected_output_row_count: int; predecessor_chunk: str | None; successor_chunk: str | None
    chunk_id: str; status: ChunkStatus = ChunkStatus.PLANNED
    def to_dict(self):
        value=asdict(self);value["status"]=self.status.value;return value


@dataclass(frozen=True)
class HistoricalRunPlan:
    run_id: str; config: HistoricalResearchRunConfig; source_fingerprints: Mapping[str,str]
    configuration_fingerprint: str; code_fingerprint: str; chunks: tuple[ChunkPlan,...]
    execution_row_count: int; warmup_rows: int
    execution_start: int = 0
    source_descriptors: Mapping[str,Mapping[str,Any]]=field(default_factory=dict)


@dataclass(frozen=True)
class HistoricalRunManifest:
    run_id: str; status: RunStatus; completed_chunks: tuple[str,...]
    pending_chunks: tuple[str,...]; continuity_frontier: int
    source_fingerprints: Mapping[str,str]; configuration_fingerprint: str; code_fingerprint: str
    warnings: tuple[str,...]=(); manifest_version: str="1.0"

    def to_dict(self):
        value=asdict(self);value["status"]=self.status.value;return value


@dataclass(frozen=True)
class ChunkCheckpoint:
    run_id: str; chunk_id: str; chunk_index: int; attempt_number: int; status: ChunkStatus
    input_fingerprint: str; configuration_fingerprint: str; code_fingerprint: str
    predecessor_final_state_fingerprint: str; initial_state_fingerprint: str
    final_state: Mapping[str,Any]; final_state_fingerprint: str; output_artifact: str
    artifact_checksum: str; input_row_count: int; output_row_count: int
    logical_start: int; logical_end: int; index_start: str | None; index_end: str | None
    schema_fingerprint: str; warnings: tuple[str,...]=(); error_summary: str=""
    timing_summary: Mapping[str,Any]=field(default_factory=dict); memory_summary: Mapping[str,Any]=field(default_factory=dict)
    checkpoint_version: str="1.0"; state_schema_version: str="1.0"
    def to_dict(self):
        value=asdict(self);value["status"]=self.status.value;return value
    @classmethod
    def from_dict(cls,value):
        data=dict(value);data["status"]=ChunkStatus(data["status"]);data["warnings"]=tuple(data.get("warnings",()));return cls(**data)


@dataclass(frozen=True)
class HistoricalRunResult:
    run_id: str; status: RunStatus; run_directory: str; completed_chunks: int; total_chunks: int
    output_rows: int; warnings: tuple[str,...]=(); timing_summary: Mapping[str,Any]=field(default_factory=dict)


@dataclass(frozen=True)
class RecoveryReport:
    run_id: str; retained_chunks: tuple[str,...]; invalidated_chunks: tuple[str,...]
    chunks_to_rerun: tuple[str,...]; orphan_files: tuple[str,...]; incompatible_files: tuple[str,...]
    recommended_action: str


@dataclass(frozen=True)
class MergeResult:
    run_id: str; artifact_path: str; row_count: int; checksum: str; schema_fingerprint: str
