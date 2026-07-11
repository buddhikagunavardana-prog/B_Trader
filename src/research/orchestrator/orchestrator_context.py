import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/research_orchestrator.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "run_id",
    "random_seed",
    "dry_run",
    "resume_enabled",
    "fail_fast",
    "continue_on_stage_failure",
    "global_task_budget",
    "global_runtime_budget_seconds",
    "output_directory",
    "state_file",
    "summary_file",
    "manifest_file",
    "smoke_mode",
    "stage_order",
    "enabled_stages",
    "stage_overrides",
]


@dataclass(frozen=True)
class OrchestratorContext:
    enabled: bool
    run_id: str
    random_seed: int
    dry_run: bool
    resume_enabled: bool
    fail_fast: bool
    continue_on_stage_failure: bool
    global_task_budget: int
    global_runtime_budget_seconds: float
    output_directory: str
    state_file: str
    summary_file: str
    manifest_file: str
    stage_order: list[str]
    enabled_stages: list[str]
    stage_overrides: dict[str, dict]
    smoke_mode: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def run_directory(self) -> Path:
        return Path(self.output_directory) / self.run_id

    def state_path(self) -> Path:
        return self.run_directory() / self.state_file

    def summary_path(self) -> Path:
        return self.run_directory() / self.summary_file

    def manifest_path(self) -> Path:
        return self.run_directory() / self.manifest_file

    def to_pipeline_context(self) -> PipelineContext:
        return PipelineContext(
            name="research_orchestrator",
            pairs=[],
            timeframe="orchestration",
            lookback="configured_stages",
            output_report=str(self.summary_path()),
            max_workers=1,
            metadata={
                "run_id": self.run_id,
                "dry_run": self.dry_run,
                "smoke_mode": self.smoke_mode,
                **self.metadata,
            },
        )

    def to_config_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "run_id": self.run_id,
            "random_seed": self.random_seed,
            "dry_run": self.dry_run,
            "resume_enabled": self.resume_enabled,
            "fail_fast": self.fail_fast,
            "continue_on_stage_failure": self.continue_on_stage_failure,
            "global_task_budget": self.global_task_budget,
            "global_runtime_budget_seconds": self.global_runtime_budget_seconds,
            "output_directory": self.output_directory,
            "state_file": self.state_file,
            "summary_file": self.summary_file,
            "manifest_file": self.manifest_file,
            "stage_order": list(self.stage_order),
            "enabled_stages": list(self.enabled_stages),
            "stage_overrides": dict(self.stage_overrides),
            "smoke_mode": self.smoke_mode,
            "metadata": dict(self.metadata),
        }


def load_orchestrator_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def build_orchestrator_context(
    config_override: dict | None = None,
) -> OrchestratorContext:
    config = load_orchestrator_config()
    if config_override:
        config.update(config_override)

    run_id = config.get("run_id") or f"run_{int(time.time())}"

    return OrchestratorContext(
        enabled=bool(config["enabled"]),
        run_id=str(run_id),
        random_seed=int(config["random_seed"]),
        dry_run=bool(config["dry_run"]),
        resume_enabled=bool(config["resume_enabled"]),
        fail_fast=bool(config["fail_fast"]),
        continue_on_stage_failure=bool(config["continue_on_stage_failure"]),
        global_task_budget=int(config["global_task_budget"]),
        global_runtime_budget_seconds=float(config["global_runtime_budget_seconds"]),
        output_directory=str(config["output_directory"]),
        state_file=str(config["state_file"]),
        summary_file=str(config["summary_file"]),
        manifest_file=str(config["manifest_file"]),
        stage_order=list(config["stage_order"]),
        enabled_stages=list(config["enabled_stages"]),
        stage_overrides=dict(config["stage_overrides"]),
        smoke_mode=bool(config.get("smoke_mode", False)),
        metadata=dict(config.get("metadata", {})),
    )
