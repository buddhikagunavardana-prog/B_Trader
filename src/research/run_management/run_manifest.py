import json
from pathlib import Path

from src.research.pipeline.pipeline_reporter import save_json_report


RUN_MANIFEST_SCHEMA_VERSION = "1"


def build_run_manifest(
    run_context,
    snapshot_index: dict,
    orchestrator_result=None,
    reproducibility_report: dict | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict:
    result_payload = orchestrator_result.to_dict() if orchestrator_result else {}
    stage_results = result_payload.get("stage_results", {})

    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_context.run_id,
        "run_name": run_context.run_name,
        "status": run_context.status,
        "created_at": run_context.created_at,
        "started_at": run_context.started_at,
        "completed_at": run_context.completed_at,
        "orchestrator_config_hash": run_context.orchestrator_config_hash,
        "stage_config_hashes": dict(run_context.stage_config_hashes),
        "repository": {
            "commit": run_context.repository_commit,
            "branch": run_context.repository_branch,
            "dirty": run_context.repository_dirty,
        },
        "environment": {
            "python_version": run_context.python_version,
            "platform": run_context.platform,
        },
        "enabled_stages": result_payload.get("planned_stages", []),
        "stage_order": result_payload.get("planned_stages", []),
        "stage_statuses": {
            stage: result.get("status", "")
            for stage, result in stage_results.items()
        },
        "config_snapshots": snapshot_index,
        "artifacts": result_payload.get("artifacts", []),
        "task_usage": result_payload.get("task_usage", 0),
        "runtime_usage": result_payload.get("runtime_usage", 0.0),
        "warnings": list(warnings or result_payload.get("warnings", [])),
        "errors": list(errors or result_payload.get("errors", [])),
        "parent_run_id": run_context.parent_run_id,
        "resume_from_run_id": run_context.resume_from_run_id,
        "tags": list(run_context.tags),
        "notes": run_context.notes,
        "metadata": {
            **dict(run_context.metadata),
            "orchestrator_result": result_payload,
            "reproducibility": reproducibility_report or {},
        },
    }


def save_run_manifest(manifest: dict, path: str | Path) -> None:
    save_json_report(manifest, str(path))


def load_run_manifest(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
