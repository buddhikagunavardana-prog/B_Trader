import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git_value(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return "UNAVAILABLE"

    if result.returncode != 0:
        return "UNAVAILABLE"

    return result.stdout.strip() or "UNKNOWN"


def collect_repository_metadata(cwd: Path | None = None) -> dict[str, Any]:
    repo_cwd = cwd or Path.cwd()
    commit = _git_value(["rev-parse", "HEAD"], repo_cwd)
    branch = _git_value(["rev-parse", "--abbrev-ref", "HEAD"], repo_cwd)
    latest_message = _git_value(["log", "-1", "--pretty=%s"], repo_cwd)
    status = _git_value(["status", "--short"], repo_cwd)
    dirty = status not in {"", "UNKNOWN", "UNAVAILABLE"}

    return {
        "commit": commit,
        "branch": branch,
        "dirty": dirty,
        "latest_commit_message": latest_message,
        "status_available": status != "UNAVAILABLE",
    }


def collect_environment_metadata() -> dict[str, str]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
    }


@dataclass
class ResearchRunContext:
    run_id: str
    run_name: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    status: str
    random_seed: int
    repository_commit: str
    repository_branch: str
    repository_dirty: bool
    python_version: str
    platform: str
    orchestrator_config_path: str
    orchestrator_config_hash: str
    stage_config_hashes: dict[str, str] = field(default_factory=dict)
    output_directory: str = ""
    snapshot_directory: str = ""
    artifact_manifest_path: str = ""
    summary_path: str = ""
    history_path: str = ""
    parent_run_id: str | None = None
    resume_from_run_id: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_name": self.run_name,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "random_seed": self.random_seed,
            "repository_commit": self.repository_commit,
            "repository_branch": self.repository_branch,
            "repository_dirty": self.repository_dirty,
            "python_version": self.python_version,
            "platform": self.platform,
            "orchestrator_config_path": self.orchestrator_config_path,
            "orchestrator_config_hash": self.orchestrator_config_hash,
            "stage_config_hashes": dict(self.stage_config_hashes),
            "output_directory": self.output_directory,
            "snapshot_directory": self.snapshot_directory,
            "artifact_manifest_path": self.artifact_manifest_path,
            "summary_path": self.summary_path,
            "history_path": self.history_path,
            "parent_run_id": self.parent_run_id,
            "resume_from_run_id": self.resume_from_run_id,
            "tags": list(self.tags),
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict):
        return cls(**payload)


def create_run_context(
    run_id: str,
    run_name: str,
    random_seed: int,
    orchestrator_config_path: str,
    orchestrator_config_hash: str,
    output_directory: str,
    snapshot_directory: str,
    artifact_manifest_path: str,
    summary_path: str,
    history_path: str,
    repository: dict | None = None,
    environment: dict | None = None,
    parent_run_id: str | None = None,
    resume_from_run_id: str | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    metadata: dict | None = None,
) -> ResearchRunContext:
    repository = repository or collect_repository_metadata()
    environment = environment or collect_environment_metadata()

    return ResearchRunContext(
        run_id=run_id,
        run_name=run_name,
        created_at=now_utc(),
        started_at=None,
        completed_at=None,
        status="CREATED",
        random_seed=random_seed,
        repository_commit=repository.get("commit", "UNKNOWN"),
        repository_branch=repository.get("branch", "UNKNOWN"),
        repository_dirty=bool(repository.get("dirty", False)),
        python_version=environment.get("python_version", "UNKNOWN"),
        platform=environment.get("platform", "UNKNOWN"),
        orchestrator_config_path=orchestrator_config_path,
        orchestrator_config_hash=orchestrator_config_hash,
        output_directory=output_directory,
        snapshot_directory=snapshot_directory,
        artifact_manifest_path=artifact_manifest_path,
        summary_path=summary_path,
        history_path=history_path,
        parent_run_id=parent_run_id,
        resume_from_run_id=resume_from_run_id,
        tags=list(tags or []),
        notes=notes,
        metadata=metadata or {},
    )
