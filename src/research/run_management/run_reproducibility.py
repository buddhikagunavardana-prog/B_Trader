from pathlib import Path

from src.research.run_management.run_snapshot import file_hash


REPRODUCIBLE = "REPRODUCIBLE"
PARTIALLY_REPRODUCIBLE = "PARTIALLY_REPRODUCIBLE"
NOT_REPRODUCIBLE = "NOT_REPRODUCIBLE"


def validate_reproducibility(manifest: dict) -> dict:
    reasons = []
    critical = []

    configs = manifest.get("config_snapshots", {}).get("configs", [])
    if not configs:
        critical.append("No config snapshots recorded")

    for config in configs:
        snapshot_path = Path(config.get("snapshot_path", ""))
        if not snapshot_path.exists():
            critical.append(f"Missing config snapshot: {config.get('filename')}")
            continue
        if file_hash(snapshot_path) != config.get("sha256"):
            critical.append(f"Config hash mismatch: {config.get('filename')}")

    repository = manifest.get("repository", {})
    commit = repository.get("commit", "UNKNOWN")
    if commit in {"UNKNOWN", "UNAVAILABLE", ""}:
        reasons.append("Repository commit is unknown")
    if repository.get("dirty", False):
        reasons.append("Repository was dirty")

    result = manifest.get("metadata", {}).get("orchestrator_result", {})
    if result.get("planned_stages") is None:
        critical.append("Stage order is not recorded")
    if manifest.get("enabled_stages") is None:
        critical.append("Enabled stages are not recorded")
    if manifest.get("metadata", {}).get("orchestrator_result", {}).get("run_id") is None:
        reasons.append("Orchestrator run id is missing")
    if not manifest.get("run_id"):
        critical.append("Run id is missing")

    for artifact in manifest.get("artifacts", []):
        if artifact.get("required", False) and not Path(artifact.get("path", "")).exists():
            critical.append(f"Missing required artifact: {artifact.get('name')}")

    if manifest.get("errors"):
        reasons.append("Run contains errors")

    if critical:
        status = NOT_REPRODUCIBLE
    elif reasons:
        status = PARTIALLY_REPRODUCIBLE
    else:
        status = REPRODUCIBLE

    return {
        "status": status,
        "reasons": reasons + critical,
        "critical_failures": critical,
    }
