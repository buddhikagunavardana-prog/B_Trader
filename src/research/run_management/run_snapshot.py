import hashlib
import json
import shutil
from pathlib import Path

from src.research.pipeline.pipeline_reporter import save_json_report


DEFAULT_CONFIG_FILES = [
    "research_orchestrator.json",
    "optimizer.json",
    "portfolio.json",
    "monte_carlo.json",
    "strategy_templates.json",
    "generated_candidate_experiment.json",
    "generated_strategy_robustness.json",
    "market_regime.json",
    "strategy.json",
    "walk_forward.json",
]


def file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_configs(
    source_directory: str | Path,
    snapshot_directory: str | Path,
    config_files: list[str] | None = None,
    required_configs: set[str] | None = None,
) -> dict:
    source_directory = Path(source_directory)
    snapshot_directory = Path(snapshot_directory)
    snapshot_directory.mkdir(parents=True, exist_ok=True)
    config_files = list(config_files or DEFAULT_CONFIG_FILES)
    required_configs = required_configs or {"research_orchestrator.json"}

    entries = []
    missing_optional = []

    for filename in config_files:
        source_path = source_directory / filename
        target_path = snapshot_directory / filename
        if not source_path.exists():
            if filename in required_configs:
                raise FileNotFoundError(f"Required config not found: {source_path}")
            missing_optional.append(filename)
            continue

        shutil.copy2(source_path, target_path)
        entries.append({
            "filename": filename,
            "source_path": str(source_path),
            "snapshot_path": str(target_path),
            "sha256": file_hash(target_path),
            "required": filename in required_configs,
            "status": "SNAPSHOTTED",
        })

    index = {
        "schema_version": "1",
        "config_count": len(entries),
        "configs": entries,
        "missing_optional": missing_optional,
    }
    save_json_report(index, str(snapshot_directory / "config_snapshot_index.json"))
    return index


def load_snapshot_index(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
