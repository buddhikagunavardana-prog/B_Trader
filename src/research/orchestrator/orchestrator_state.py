import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ORCHESTRATOR_VERSION = "20.3"


def calculate_config_hash(config: dict) -> str:
    import hashlib

    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class OrchestratorState:
    run_id: str
    config_hash: str
    created_at: str
    updated_at: str
    orchestrator_version: str = ORCHESTRATOR_VERSION
    current_stage: str | None = None
    completed_stages: list[str] = field(default_factory=list)
    failed_stages: list[str] = field(default_factory=list)
    blocked_stages: list[str] = field(default_factory=list)
    skipped_stages: list[str] = field(default_factory=list)
    stage_results: dict[str, dict] = field(default_factory=dict)
    artifact_manifest: list[dict] = field(default_factory=list)
    task_usage: int = 0
    runtime_usage: float = 0.0
    status: str = "PENDING"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, context):
        now = _now()
        return cls(
            run_id=context.run_id,
            config_hash=calculate_config_hash(context.to_config_dict()),
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_dict(cls, data: dict):
        if data.get("orchestrator_version") != ORCHESTRATOR_VERSION:
            raise ValueError("Incompatible orchestrator state version")

        return cls(**data)

    def touch(self):
        self.updated_at = _now()

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "orchestrator_version": self.orchestrator_version,
            "config_hash": self.config_hash,
            "current_stage": self.current_stage,
            "completed_stages": list(self.completed_stages),
            "failed_stages": list(self.failed_stages),
            "blocked_stages": list(self.blocked_stages),
            "skipped_stages": list(self.skipped_stages),
            "stage_results": dict(self.stage_results),
            "artifact_manifest": list(self.artifact_manifest),
            "task_usage": self.task_usage,
            "runtime_usage": self.runtime_usage,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


def save_state_atomic(state: OrchestratorState, path: Path) -> None:
    os.makedirs(path.parent, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(state.to_dict(), file, indent=4)

    os.replace(tmp_path, path)


def load_state(path: Path, expected_config_hash: str | None = None) -> OrchestratorState:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    state = OrchestratorState.from_dict(data)
    if expected_config_hash and state.config_hash != expected_config_hash:
        raise ValueError("Incompatible orchestrator state config hash")

    return state


def validate_completed_stage_artifacts(
    state: OrchestratorState,
    stage_name: str,
    expected_contract_version: str | None = None,
    expected_metadata: dict | None = None,
) -> bool:
    artifacts = [
        artifact
        for artifact in state.artifact_manifest
        if artifact.get("producer_stage") == stage_name
        and artifact.get("required", False)
    ]

    if expected_contract_version is not None and any(
        str(artifact.get("metadata", {}).get("contract_version"))
        != str(expected_contract_version)
        for artifact in artifacts
    ):
        return False
    if expected_metadata and any(
        any(
            artifact.get("metadata", {}).get(key) != value
            for key, value in expected_metadata.items()
        )
        for artifact in artifacts
    ):
        return False
    return all(Path(artifact["path"]).exists() for artifact in artifacts)
