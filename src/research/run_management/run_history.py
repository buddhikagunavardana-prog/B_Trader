import json
import os
from pathlib import Path


RUN_HISTORY_SCHEMA_VERSION = "1"
FINAL_STATUSES = {"COMPLETED", "FAILED", "DISABLED", "DRY_RUN"}


def _write_json_atomic(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)
    os.replace(tmp_path, path)


def load_run_history(path: str | Path) -> dict:
    history_path = Path(path)
    if not history_path.exists():
        return {"schema_version": RUN_HISTORY_SCHEMA_VERSION, "runs": []}

    try:
        with open(history_path, "r", encoding="utf-8") as file:
            history = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"Run history is corrupt: {history_path}") from error

    if history.get("schema_version") != RUN_HISTORY_SCHEMA_VERSION:
        raise ValueError("Unsupported run history schema version")

    history.setdefault("runs", [])
    return history


def build_history_entry(run_context, manifest: dict, summary_path: str, manifest_path: str) -> dict:
    return {
        "run_id": run_context.run_id,
        "run_name": run_context.run_name,
        "status": run_context.status,
        "created_at": run_context.created_at,
        "completed_at": run_context.completed_at,
        "elapsed_seconds": manifest.get("metadata", {})
        .get("orchestrator_result", {})
        .get("elapsed_seconds", 0.0),
        "repository_commit": run_context.repository_commit,
        "orchestrator_config_hash": run_context.orchestrator_config_hash,
        "enabled_stages": list(manifest.get("enabled_stages", [])),
        "artifact_count": len(manifest.get("artifacts", [])),
        "summary_path": summary_path,
        "manifest_path": manifest_path,
        "parent_run_id": run_context.parent_run_id,
        "tags": list(run_context.tags),
        "notes": run_context.notes,
    }


def upsert_run_history_entry(
    history_path: str | Path,
    entry: dict,
    update_existing: bool = False,
) -> dict:
    history_path = Path(history_path)
    history = load_run_history(history_path)
    runs = history["runs"]

    for index, existing in enumerate(runs):
        if existing.get("run_id") == entry["run_id"]:
            if update_existing or existing.get("status") not in FINAL_STATUSES:
                runs[index] = entry
                runs.sort(key=lambda item: item.get("created_at", ""))
                _write_json_atomic(history, history_path)
                return history
            raise ValueError(f"Duplicate completed run id: {entry['run_id']}")

    runs.append(entry)
    runs.sort(key=lambda item: item.get("created_at", ""))
    _write_json_atomic(history, history_path)
    return history
