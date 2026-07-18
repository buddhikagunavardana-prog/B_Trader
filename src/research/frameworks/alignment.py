from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from src.research.frameworks.exceptions import ResearchAlignmentError
from src.research.frameworks.models import AlignmentDiagnostic, PreparedTimeframeData


@dataclass(frozen=True)
class CausalAlignment:
    timeline: pd.DatetimeIndex
    positions: Mapping[str, tuple[int, ...]]
    source_timestamps: Mapping[str, tuple[pd.Timestamp | None, ...]]


def build_causal_alignment(prepared: Mapping[str, PreparedTimeframeData], primary_role: str, start=None, end=None) -> CausalAlignment:
    if primary_role not in prepared:
        raise ResearchAlignmentError(f"primary role not prepared: {primary_role}")
    timeline = prepared[primary_role].frame.index
    if start is not None:
        timeline = timeline[timeline >= pd.Timestamp(start)]
    if end is not None:
        timeline = timeline[timeline <= pd.Timestamp(end)]
    positions: dict[str, tuple[int, ...]] = {}; sources: dict[str, tuple[pd.Timestamp | None, ...]] = {}
    for role, item in prepared.items():
        index = item.frame.index
        try:
            role_positions = tuple(int(index.searchsorted(ts, side="right")) for ts in timeline)
        except TypeError as error:
            raise ResearchAlignmentError(f"timezone mismatch for role '{role}'") from error
        positions[role] = role_positions
        sources[role] = tuple(pd.Timestamp(index[pos - 1]) if pos else None for pos in role_positions)
    return CausalAlignment(timeline, positions, sources)


def alignment_diagnostics(alignment: CausalAlignment, row: int) -> dict[str, AlignmentDiagnostic]:
    timestamp = pd.Timestamp(alignment.timeline[row]); result = {}
    for role, sources in alignment.source_timestamps.items():
        source = sources[row]
        missing = source is None
        age = None if missing else float((timestamp - source).total_seconds())
        result[role] = AlignmentDiagnostic(role, timestamp, source, not missing and source <= timestamp, missing, age, "missing completed bar" if missing else "")
    return result
