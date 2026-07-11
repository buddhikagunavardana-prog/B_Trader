from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    seed: int
    requested_budget: int
    selected_count: int
    rejected_count: int
    duplicate_count: int
    attempt_count: int
    exhausted: bool
    early_stopped: bool
    stop_reason: str
    candidate_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "seed": self.seed,
            "requested_budget": self.requested_budget,
            "selected_count": self.selected_count,
            "rejected_count": self.rejected_count,
            "duplicate_count": self.duplicate_count,
            "attempt_count": self.attempt_count,
            "exhausted": self.exhausted,
            "early_stopped": self.early_stopped,
            "stop_reason": self.stop_reason,
            "candidate_ids": list(self.candidate_ids),
            "metadata": dict(self.metadata),
        }
