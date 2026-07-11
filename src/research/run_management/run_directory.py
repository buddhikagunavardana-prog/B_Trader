from dataclasses import dataclass
from pathlib import Path

from src.research.run_management.run_identity import validate_run_id


@dataclass(frozen=True)
class RunDirectoryLayout:
    base_directory: Path
    run_id: str
    run_directory: Path
    configs_directory: Path
    state_directory: Path
    artifacts_directory: Path
    summaries_directory: Path
    logs_directory: Path
    comparisons_directory: Path
    manifest_path: Path
    summary_path: Path
    orchestrator_state_path: Path


def build_run_directory_layout(
    base_output_directory: str | Path,
    run_id: str,
) -> RunDirectoryLayout:
    validate_run_id(run_id)
    base_directory = Path(base_output_directory)
    run_directory = base_directory / run_id

    return RunDirectoryLayout(
        base_directory=base_directory,
        run_id=run_id,
        run_directory=run_directory,
        configs_directory=run_directory / "configs",
        state_directory=run_directory / "state",
        artifacts_directory=run_directory / "artifacts",
        summaries_directory=run_directory / "summaries",
        logs_directory=run_directory / "logs",
        comparisons_directory=run_directory / "comparisons",
        manifest_path=run_directory / "manifest.json",
        summary_path=run_directory / "run_summary.json",
        orchestrator_state_path=run_directory / "orchestrator_state.json",
    )


def create_run_directories(
    layout: RunDirectoryLayout,
    prevent_overwrite: bool = True,
    resume: bool = False,
) -> None:
    if layout.run_directory.exists() and prevent_overwrite and not resume:
        raise FileExistsError(f"Run directory already exists: {layout.run_directory}")

    for directory in [
        layout.run_directory,
        layout.configs_directory,
        layout.state_directory,
        layout.artifacts_directory,
        layout.summaries_directory,
        layout.logs_directory,
        layout.comparisons_directory,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def validate_run_directory(layout: RunDirectoryLayout) -> None:
    if not layout.run_directory.exists():
        raise FileNotFoundError(f"Run directory not found: {layout.run_directory}")

    for directory in [
        layout.configs_directory,
        layout.state_directory,
        layout.artifacts_directory,
        layout.summaries_directory,
        layout.logs_directory,
        layout.comparisons_directory,
    ]:
        if not directory.exists():
            raise FileNotFoundError(f"Run subdirectory not found: {directory}")
