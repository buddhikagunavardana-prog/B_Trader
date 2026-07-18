from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from src.research.frameworks.models import FrameworkResearchConfiguration, PreparedTimeframeData
from src.research.frameworks.profiling.models import DiagnosticLevel, SnapshotMode
from src.research.frameworks.profiling.session import SessionRuntimeContext
from src.research.frameworks.state.session_state import SessionConfiguration
from src.research.run_management.run_identity import stable_identity_hash


def augment_runtime_columns(framework, prepared):
    """Add bounded, causal run-owned columns for measured framework hotspots."""
    if getattr(getattr(framework, "spec", None), "kind", None) != "opening_range":
        return prepared
    frame = prepared["execution"].frame
    opening_bars = int(framework.parameters["opening_bars"])
    session_keys = frame.index.normalize()
    grouped_high = frame["high"].groupby(session_keys, sort=False)
    grouped_low = frame["low"].groupby(session_keys, sort=False)
    frame["__bt_opening_high"] = grouped_high.transform(lambda values: values.iloc[:opening_bars].max())
    frame["__bt_opening_low"] = grouped_low.transform(lambda values: values.iloc[:opening_bars].min())
    frame["__bt_opening_complete"] = grouped_high.cumcount() >= opening_bars
    return prepared


def diagnostic_level(configuration: FrameworkResearchConfiguration) -> DiagnosticLevel:
    if not configuration.include_diagnostics:
        return DiagnosticLevel.NONE
    return DiagnosticLevel(str(configuration.state_diagnostics_level).lower())


def snapshot_mode(configuration: FrameworkResearchConfiguration) -> SnapshotMode:
    value = configuration.persist_state_snapshots
    if isinstance(value, bool):
        return SnapshotMode.FULL if value else SnapshotMode.NONE
    return SnapshotMode(str(value).lower())


@dataclass(frozen=True)
class FrameworkRuntimeContext:
    configuration_fingerprint: str
    dependency_fingerprints: tuple[str, ...]
    prepared: Mapping[str, PreparedTimeframeData]
    session: SessionRuntimeContext
    diagnostics: DiagnosticLevel
    snapshots: SnapshotMode
    instrumentation_enabled: bool
    row_count: int

    @classmethod
    def build(cls, configuration, prepared, alignment) -> "FrameworkRuntimeContext":
        fingerprints = sorted({
            fingerprint
            for item in prepared.values()
            for fingerprint in item.metadata.get("dependency_request_fingerprints", ())
        })
        return cls(
            stable_identity_hash(configuration.to_dict()), tuple(fingerprints),
            MappingProxyType(dict(prepared)),
            SessionRuntimeContext.build(
                alignment.timeline,
                SessionConfiguration.from_mapping(configuration.session_configuration),
            ),
            diagnostic_level(configuration), snapshot_mode(configuration),
            configuration.enable_controller_timing, len(alignment.timeline),
        )

    def summary(self) -> dict[str, object]:
        return {
            "configuration_fingerprint": self.configuration_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "diagnostic_level": self.diagnostics.value,
            "snapshot_mode": self.snapshots.value,
            "instrumentation_enabled": self.instrumentation_enabled,
            "row_count": self.row_count,
        }
