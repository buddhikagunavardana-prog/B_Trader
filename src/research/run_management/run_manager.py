from pathlib import Path

from src.research.orchestrator.orchestrator_runner import run_research_orchestrator
from src.research.orchestrator.orchestrator_state import calculate_config_hash
from src.research.pipeline.pipeline_loader import load_json_config
from src.research.pipeline.pipeline_reporter import save_json_report
from src.research.run_management.run_context import (
    collect_environment_metadata,
    collect_repository_metadata,
    create_run_context,
    now_utc,
)
from src.research.run_management.run_directory import (
    build_run_directory_layout,
    create_run_directories,
)
from src.research.run_management.run_history import (
    build_history_entry,
    upsert_run_history_entry,
)
from src.research.run_management.run_identity import (
    generate_run_id,
    sanitize_run_name,
)
from src.research.run_management.run_manifest import (
    build_run_manifest,
    save_run_manifest,
)
from src.research.run_management.run_report import write_run_reports
from src.research.run_management.run_reproducibility import (
    validate_reproducibility,
)
from src.research.run_management.run_snapshot import snapshot_configs


CONFIG_PATH = Path("src/config/research_run_management.json")
ORCHESTRATOR_CONFIG_PATH = Path("src/config/research_orchestrator.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "base_output_directory",
    "history_file",
    "snapshot_configs",
    "capture_git_metadata",
    "capture_environment_metadata",
    "prevent_overwrite",
    "validate_reproducibility",
    "allow_resume",
    "allow_child_runs",
    "default_tags",
    "default_notes",
    "write_stage_csv",
]


def load_run_management_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def _merge_orchestrator_config(orchestrator_override: dict | None = None) -> dict:
    config = load_json_config(ORCHESTRATOR_CONFIG_PATH)
    if orchestrator_override:
        config.update(orchestrator_override)
    return config


def _disabled_result(config: dict) -> dict:
    return {
        "status": "DISABLED",
        "run_id": None,
        "message": "Research run management is disabled",
        "config": config,
    }


def run_research_run_management(
    config_override: dict | None = None,
    orchestrator_override: dict | None = None,
    orchestrator_runner=run_research_orchestrator,
) -> dict:
    manager_config = load_run_management_config()
    if config_override:
        manager_config.update(config_override)

    if not manager_config["enabled"]:
        return _disabled_result(manager_config)

    orchestrator_config = _merge_orchestrator_config(orchestrator_override)
    run_name = sanitize_run_name(manager_config.get("run_name"))
    run_id = manager_config.get("run_id") or generate_run_id(
        orchestrator_config,
        run_name=run_name,
    )
    base_output_directory = Path(manager_config["base_output_directory"])
    layout = build_run_directory_layout(base_output_directory, run_id)
    resume = bool(manager_config.get("resume_from_run_id")) or bool(
        manager_config.get("resume", False)
    )
    create_run_directories(
        layout,
        prevent_overwrite=bool(manager_config["prevent_overwrite"]),
        resume=resume and bool(manager_config["allow_resume"]),
    )

    snapshot_index = {
        "schema_version": "1",
        "config_count": 0,
        "configs": [],
        "missing_optional": [],
    }
    if manager_config["snapshot_configs"]:
        snapshot_index = snapshot_configs("src/config", layout.configs_directory)

    stage_config_hashes = {
        item["filename"]: item["sha256"]
        for item in snapshot_index.get("configs", [])
    }
    orchestrator_config_hash = calculate_config_hash(orchestrator_config)
    repository = (
        collect_repository_metadata()
        if manager_config["capture_git_metadata"]
        else {"commit": "UNAVAILABLE", "branch": "UNAVAILABLE", "dirty": False}
    )
    environment = (
        collect_environment_metadata()
        if manager_config["capture_environment_metadata"]
        else {"python_version": "UNAVAILABLE", "platform": "UNAVAILABLE"}
    )
    tags = list(manager_config.get("default_tags", []))
    tags.extend(manager_config.get("tags", []))

    run_context = create_run_context(
        run_id=run_id,
        run_name=run_name,
        random_seed=int(orchestrator_config.get("random_seed", 42)),
        orchestrator_config_path=str(ORCHESTRATOR_CONFIG_PATH),
        orchestrator_config_hash=orchestrator_config_hash,
        output_directory=str(layout.run_directory),
        snapshot_directory=str(layout.configs_directory),
        artifact_manifest_path=str(layout.manifest_path),
        summary_path=str(layout.summary_path),
        history_path=str(base_output_directory / manager_config["history_file"]),
        repository=repository,
        environment=environment,
        parent_run_id=manager_config.get("parent_run_id"),
        resume_from_run_id=manager_config.get("resume_from_run_id"),
        tags=tags,
        notes=str(manager_config.get("notes", manager_config["default_notes"])),
        metadata={"manager_config": manager_config},
    )
    run_context.stage_config_hashes = stage_config_hashes
    run_context.status = "RUNNING"
    run_context.started_at = now_utc()

    orchestrator_config.update({
        "enabled": bool(orchestrator_config.get("enabled", False)),
        "run_id": run_id,
        "output_directory": str(base_output_directory),
        "resume_enabled": bool(manager_config["allow_resume"]),
    })
    orchestrator_result = orchestrator_runner(orchestrator_config)
    run_context.status = orchestrator_result.status
    run_context.completed_at = now_utc()

    manifest = build_run_manifest(
        run_context,
        snapshot_index,
        orchestrator_result=orchestrator_result,
    )
    reproducibility_report = (
        validate_reproducibility(manifest)
        if manager_config["validate_reproducibility"]
        else {"status": "NOT_VALIDATED", "reasons": [], "critical_failures": []}
    )
    manifest = build_run_manifest(
        run_context,
        snapshot_index,
        orchestrator_result=orchestrator_result,
        reproducibility_report=reproducibility_report,
    )
    save_run_manifest(manifest, layout.manifest_path)
    save_json_report(snapshot_index, str(layout.configs_directory / "config_snapshot_index.json"))

    summary = write_run_reports(
        run_context,
        manifest,
        reproducibility_report,
        layout.summary_path,
        layout.summaries_directory / "reproducibility_report.json",
        layout.summaries_directory / "run_stage_summary.csv"
        if manager_config["write_stage_csv"]
        else None,
    )
    history_path = base_output_directory / manager_config["history_file"]
    history_entry = build_history_entry(
        run_context,
        manifest,
        str(layout.summary_path),
        str(layout.manifest_path),
    )
    history = upsert_run_history_entry(
        history_path,
        history_entry,
        update_existing=resume,
    )

    return {
        "status": run_context.status,
        "run_id": run_id,
        "run_context": run_context.to_dict(),
        "manifest": manifest,
        "summary": summary,
        "snapshot_index": snapshot_index,
        "reproducibility": reproducibility_report,
        "history": history,
        "orchestrator_result": orchestrator_result.to_dict(),
    }


def main() -> None:
    result = run_research_run_management()
    print(
        "Research run management "
        f"{result['status']}: run_id={result.get('run_id')}"
    )


if __name__ == "__main__":
    main()
