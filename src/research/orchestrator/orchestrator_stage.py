from dataclasses import dataclass, field, replace
from typing import Any, Callable


STAGE_PENDING = "PENDING"
STAGE_SKIPPED = "SKIPPED"
STAGE_RUNNING = "RUNNING"
STAGE_COMPLETED = "COMPLETED"
STAGE_FAILED = "FAILED"
STAGE_BLOCKED = "BLOCKED"
STAGE_CANCELLED = "CANCELLED"

VALID_STAGE_STATUSES = {
    STAGE_PENDING,
    STAGE_SKIPPED,
    STAGE_RUNNING,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_BLOCKED,
    STAGE_CANCELLED,
}


@dataclass(frozen=True)
class OrchestratorStage:
    name: str
    display_name: str
    enabled: bool = True
    required: bool = True
    dependencies: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    runner: Callable | None = None
    status: str = STAGE_PENDING
    task_budget: int | None = None
    runtime_budget_seconds: float | None = None
    allow_resume: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **updates):
        return replace(self, **updates)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "required": self.required,
            "dependencies": list(self.dependencies),
            "input_artifacts": list(self.input_artifacts),
            "output_artifacts": list(self.output_artifacts),
            "status": self.status,
            "task_budget": self.task_budget,
            "runtime_budget_seconds": self.runtime_budget_seconds,
            "allow_resume": self.allow_resume,
            "metadata": dict(self.metadata),
        }
