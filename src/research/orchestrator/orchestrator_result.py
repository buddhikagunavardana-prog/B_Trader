from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrchestratorResult:
    run_id: str
    status: str
    started_at: str
    completed_at: str
    elapsed_seconds: float
    planned_stages: list[str]
    completed_stages: list[str]
    failed_stages: list[str]
    blocked_stages: list[str]
    skipped_stages: list[str]
    stage_results: dict[str, dict]
    artifacts: list[dict]
    task_usage: int
    runtime_usage: float
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_seconds": self.elapsed_seconds,
            "planned_stages": list(self.planned_stages),
            "completed_stages": list(self.completed_stages),
            "failed_stages": list(self.failed_stages),
            "blocked_stages": list(self.blocked_stages),
            "skipped_stages": list(self.skipped_stages),
            "stage_results": dict(self.stage_results),
            "artifacts": list(self.artifacts),
            "task_usage": self.task_usage,
            "runtime_usage": self.runtime_usage,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }
