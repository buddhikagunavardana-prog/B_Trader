from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PipelineContext:
    name: str
    pairs: list[str]
    timeframe: str
    lookback: str
    output_report: str | None = None
    max_workers: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineTask:
    item_index: int
    pair_index: int
    pair: str
    payload: Any
    timeframe: str
    metadata: dict[str, Any] = field(default_factory=dict)
