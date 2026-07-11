import hashlib
import json
import re
import time
from pathlib import Path

from src.research.orchestrator.orchestrator_state import calculate_config_hash


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sanitize_run_name(run_name: str | None) -> str:
    if not run_name:
        return "research_run"

    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", run_name.strip())
    sanitized = sanitized.strip("._-")
    return sanitized or "research_run"


def validate_run_id(run_id: str) -> None:
    if not run_id or not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"Invalid run id: {run_id}")

    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise ValueError(f"Run id cannot contain path traversal: {run_id}")


def stable_identity_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]


def generate_run_id(
    orchestrator_config: dict,
    run_name: str | None = None,
    timestamp: str | None = None,
) -> str:
    safe_name = sanitize_run_name(run_name)
    stamp = timestamp or time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    identity_payload = {
        "config_hash": calculate_config_hash(orchestrator_config),
        "random_seed": orchestrator_config.get("random_seed"),
        "enabled_stages": orchestrator_config.get("enabled_stages", []),
        "stage_overrides": orchestrator_config.get("stage_overrides", {}),
    }
    run_id = f"{safe_name}_{stamp}_{stable_identity_hash(identity_payload)}"
    validate_run_id(run_id)
    return run_id


def ensure_unique_run_id(
    base_output_directory: str | Path,
    run_id: str,
    allow_resume: bool = False,
) -> None:
    validate_run_id(run_id)
    run_path = Path(base_output_directory) / run_id
    if run_path.exists() and not allow_resume:
        raise FileExistsError(f"Run directory already exists: {run_path}")
