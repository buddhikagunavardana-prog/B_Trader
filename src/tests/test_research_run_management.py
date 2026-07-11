from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.orchestrator.orchestrator_result import OrchestratorResult
from src.research.run_management.run_comparison import compare_run_manifests
from src.research.run_management.run_context import (
    collect_environment_metadata,
    create_run_context,
    now_utc,
)
from src.research.run_management.run_directory import (
    build_run_directory_layout,
    create_run_directories,
    validate_run_directory,
)
from src.research.run_management.run_history import (
    build_history_entry,
    load_run_history,
    upsert_run_history_entry,
)
from src.research.run_management.run_identity import (
    ensure_unique_run_id,
    generate_run_id,
    sanitize_run_name,
    validate_run_id,
)
from src.research.run_management.run_manager import (
    load_run_management_config,
    run_research_run_management,
)
from src.research.run_management.run_manifest import (
    RUN_MANIFEST_SCHEMA_VERSION,
    build_run_manifest,
    load_run_manifest,
    save_run_manifest,
)
from src.research.run_management.run_report import build_run_summary
from src.research.run_management.run_reproducibility import (
    NOT_REPRODUCIBLE,
    PARTIALLY_REPRODUCIBLE,
    REPRODUCIBLE,
    validate_reproducibility,
)
from src.research.run_management.run_snapshot import (
    file_hash,
    load_snapshot_index,
    snapshot_configs,
)


def _orchestrator_config() -> dict:
    return {
        "enabled": True,
        "random_seed": 42,
        "enabled_stages": ["load_data"],
        "stage_overrides": {},
    }


def _fake_result(run_id: str, artifact_path: Path | None = None) -> OrchestratorResult:
    artifacts = []
    if artifact_path:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("ok", encoding="utf-8")
        artifacts.append({
            "name": "fake_artifact",
            "artifact_type": "JSON",
            "path": str(artifact_path),
            "producer_stage": "fake",
            "schema_version": "1",
            "required": True,
            "status": "CREATED",
            "metadata": {},
        })

    return OrchestratorResult(
        run_id=run_id,
        status="COMPLETED",
        started_at=now_utc(),
        completed_at=now_utc(),
        elapsed_seconds=0.01,
        planned_stages=["fake"],
        completed_stages=["fake"],
        failed_stages=[],
        blocked_stages=[],
        skipped_stages=[],
        stage_results={
            "fake": {
                "status": "COMPLETED",
                "task_usage": 1,
                "runtime_seconds": 0.01,
                "artifacts": artifacts,
                "message": "done",
            }
        },
        artifacts=artifacts,
        task_usage=1,
        runtime_usage=0.01,
        warnings=[],
        errors=[],
        metadata={},
    )


def _fake_orchestrator(config: dict) -> OrchestratorResult:
    run_id = config["run_id"]
    artifact_path = Path(config["output_directory"]) / run_id / "fake_artifact.json"
    return _fake_result(run_id, artifact_path)


def _run_context(directory: str, dirty: bool = False):
    return create_run_context(
        run_id="unit_run",
        run_name="unit",
        random_seed=42,
        orchestrator_config_path="src/config/research_orchestrator.json",
        orchestrator_config_hash="abc",
        output_directory=str(Path(directory) / "unit_run"),
        snapshot_directory=str(Path(directory) / "unit_run" / "configs"),
        artifact_manifest_path=str(Path(directory) / "unit_run" / "manifest.json"),
        summary_path=str(Path(directory) / "unit_run" / "run_summary.json"),
        history_path=str(Path(directory) / "run_history.json"),
        repository={"commit": "abc123", "branch": "main", "dirty": dirty},
        environment={"python_version": "3.x", "platform": "unit"},
        tags=["unit"],
        notes="note",
    )


def _snapshot_with_required_config(directory: str) -> dict:
    source = Path(directory) / "configs"
    source.mkdir(exist_ok=True)
    (source / "research_orchestrator.json").write_text('{"enabled": false}', encoding="utf-8")
    return snapshot_configs(source, Path(directory) / "snapshots")


def test_config_loading_and_disabled_behavior():
    config = load_run_management_config()
    result = run_research_run_management({"enabled": False})

    assert config["enabled"] is False
    assert result["status"] == "DISABLED"


def test_run_id_generation_and_name_sanitization():
    run_id = generate_run_id(
        _orchestrator_config(),
        run_name="My Run/One",
        timestamp="20260101_000000",
    )

    assert run_id.startswith("My_Run_One_20260101_000000")
    assert sanitize_run_name("../bad name") == "bad_name"
    validate_run_id(run_id)


def test_invalid_run_id_rejects_path_traversal():
    try:
        validate_run_id("../bad")
    except ValueError as error:
        assert "Invalid run id" in str(error) or "path traversal" in str(error)
    else:
        raise AssertionError("Invalid run id did not fail")


def test_collision_prevention():
    with TemporaryDirectory() as directory:
        Path(directory, "same_run").mkdir()
        try:
            ensure_unique_run_id(directory, "same_run", allow_resume=False)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Collision did not fail")

        ensure_unique_run_id(directory, "same_run", allow_resume=True)


def test_directory_creation_overwrite_and_resume_validation():
    with TemporaryDirectory() as directory:
        layout = build_run_directory_layout(directory, "unit_run")
        create_run_directories(layout)
        validate_run_directory(layout)

        try:
            create_run_directories(layout, prevent_overwrite=True, resume=False)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Overwrite did not fail")

        create_run_directories(layout, prevent_overwrite=True, resume=True)


def test_config_snapshot_creation_and_hashing():
    with TemporaryDirectory() as directory:
        snapshot = _snapshot_with_required_config(directory)
        index_path = Path(directory, "snapshots", "config_snapshot_index.json")
        loaded = load_snapshot_index(index_path)

        assert snapshot["config_count"] == 1
        assert loaded["configs"][0]["sha256"] == file_hash(
            loaded["configs"][0]["snapshot_path"]
        )


def test_missing_required_config_error_and_optional_handling():
    with TemporaryDirectory() as directory:
        source = Path(directory) / "configs"
        source.mkdir()
        try:
            snapshot_configs(source, Path(directory) / "snapshots")
        except FileNotFoundError as error:
            assert "Required config" in str(error)
        else:
            raise AssertionError("Missing required config did not fail")

        (source / "research_orchestrator.json").write_text("{}", encoding="utf-8")
        snapshot = snapshot_configs(
            source,
            Path(directory) / "snapshots",
            config_files=["research_orchestrator.json", "optional.json"],
        )
        assert snapshot["missing_optional"] == ["optional.json"]


def test_repository_metadata_fallback_and_environment_metadata():
    environment = collect_environment_metadata()
    context = create_run_context(
        run_id="unit",
        run_name="unit",
        random_seed=42,
        orchestrator_config_path="x",
        orchestrator_config_hash="h",
        output_directory="out",
        snapshot_directory="snap",
        artifact_manifest_path="manifest",
        summary_path="summary",
        history_path="history",
        repository={"commit": "UNAVAILABLE", "branch": "UNAVAILABLE", "dirty": False},
        environment=environment,
    )

    assert context.repository_commit == "UNAVAILABLE"
    assert context.python_version


def test_manifest_creation_schema_and_artifact_references():
    with TemporaryDirectory() as directory:
        snapshot = _snapshot_with_required_config(directory)
        context = _run_context(directory)
        result = _fake_result("unit_run", Path(directory, "artifact.json"))
        manifest = build_run_manifest(context, snapshot, result)

        assert manifest["schema_version"] == RUN_MANIFEST_SCHEMA_VERSION
        assert manifest["artifacts"][0]["name"] == "fake_artifact"


def test_manifest_save_and_load():
    with TemporaryDirectory() as directory:
        manifest_path = Path(directory, "manifest.json")
        manifest = {"schema_version": RUN_MANIFEST_SCHEMA_VERSION, "run_id": "unit"}
        save_run_manifest(manifest, manifest_path)

        assert load_run_manifest(manifest_path)["run_id"] == "unit"


def test_history_append_duplicate_update_and_corruption():
    with TemporaryDirectory() as directory:
        context = _run_context(directory)
        context.status = "COMPLETED"
        manifest = {"enabled_stages": [], "artifacts": [], "metadata": {}}
        entry = build_history_entry(context, manifest, "summary.json", "manifest.json")
        history_path = Path(directory, "history.json")
        upsert_run_history_entry(history_path, entry)

        try:
            upsert_run_history_entry(history_path, entry)
        except ValueError as error:
            assert "Duplicate" in str(error)
        else:
            raise AssertionError("Duplicate history entry did not fail")

        entry["status"] = "FAILED"
        upsert_run_history_entry(history_path, entry, update_existing=True)
        assert load_run_history(history_path)["runs"][0]["status"] == "FAILED"

        bad_path = Path(directory, "bad_history.json")
        bad_path.write_text("{bad", encoding="utf-8")
        try:
            load_run_history(bad_path)
        except ValueError as error:
            assert "corrupt" in str(error)
        else:
            raise AssertionError("Corrupt history did not fail")


def test_comparison_with_same_changed_and_missing_metrics():
    base = {
        "run_id": "base",
        "repository": {"commit": "abc"},
        "enabled_stages": ["a"],
        "config_snapshots": {"configs": [{"filename": "a.json", "sha256": "1"}]},
        "artifacts": [],
    }
    same = {
        **base,
        "run_id": "same",
        "repository": {"commit": "abc"},
    }
    changed = {
        **base,
        "run_id": "changed",
        "repository": {"commit": "def"},
        "enabled_stages": ["b"],
        "config_snapshots": {"configs": [{"filename": "a.json", "sha256": "2"}]},
    }

    assert compare_run_manifests(base, same)["conclusion"] == "MATCH"
    comparison = compare_run_manifests(base, changed)
    assert comparison["conclusion"] == "DIFFERENT"
    assert comparison["changed_configs"] == ["a.json"]


def test_reproducibility_success_dirty_partial_missing_snapshot_and_artifact_failure():
    with TemporaryDirectory() as directory:
        snapshot = _snapshot_with_required_config(directory)
        context = _run_context(directory)
        result = _fake_result("unit_run", Path(directory, "artifact.json"))
        manifest = build_run_manifest(context, snapshot, result)

        assert validate_reproducibility(manifest)["status"] == REPRODUCIBLE

        dirty_context = _run_context(directory, dirty=True)
        dirty_manifest = build_run_manifest(dirty_context, snapshot, result)
        assert validate_reproducibility(dirty_manifest)["status"] == PARTIALLY_REPRODUCIBLE

        Path(snapshot["configs"][0]["snapshot_path"]).unlink()
        assert validate_reproducibility(manifest)["status"] == NOT_REPRODUCIBLE

        snapshot = _snapshot_with_required_config(directory)
        missing_artifact = build_run_manifest(
            context,
            snapshot,
            _fake_result("unit_run", Path(directory, "missing_artifact.json")),
        )
        Path(missing_artifact["artifacts"][0]["path"]).unlink()
        assert validate_reproducibility(missing_artifact)["status"] == NOT_REPRODUCIBLE


def test_run_summary_schema():
    with TemporaryDirectory() as directory:
        snapshot = _snapshot_with_required_config(directory)
        context = _run_context(directory)
        result = _fake_result("unit_run", Path(directory, "artifact.json"))
        manifest = build_run_manifest(context, snapshot, result)
        reproducibility = validate_reproducibility(manifest)
        summary = build_run_summary(context, manifest, reproducibility)

        assert summary["Run ID"] == "unit_run"
        assert "Reproducibility Status" in summary


def test_dry_run_management_and_existing_orchestrator_compatibility():
    with TemporaryDirectory() as directory:
        result = run_research_run_management(
            {
                "enabled": True,
                "base_output_directory": directory,
                "run_id": "dry_manager",
                "run_name": "dry manager",
                "prevent_overwrite": True,
                "capture_git_metadata": False,
            },
            {
                "enabled": True,
                "dry_run": True,
                "smoke_mode": True,
                "enabled_stages": [],
            },
        )

        assert result["status"] == "DRY_RUN"
        assert Path(directory, "dry_manager", "manifest.json").exists()


def test_manager_with_fake_orchestrator_smoke_resume_and_parent_child():
    with TemporaryDirectory() as directory:
        base_config = {
            "enabled": True,
            "base_output_directory": directory,
            "run_id": "managed_smoke",
            "run_name": "managed smoke",
            "prevent_overwrite": True,
            "capture_git_metadata": False,
        }
        first = run_research_run_management(
            base_config,
            {"enabled": True, "dry_run": False, "smoke_mode": True},
            orchestrator_runner=_fake_orchestrator,
        )
        resume = run_research_run_management(
            {**base_config, "resume": True},
            {"enabled": True, "dry_run": False, "smoke_mode": True},
            orchestrator_runner=_fake_orchestrator,
        )
        child = run_research_run_management(
            {
                **base_config,
                "run_id": "managed_child",
                "parent_run_id": first["run_id"],
            },
            {"enabled": True, "dry_run": False, "smoke_mode": True},
            orchestrator_runner=_fake_orchestrator,
        )
        comparison = compare_run_manifests(first["manifest"], child["manifest"])

        assert first["status"] == "COMPLETED"
        assert resume["status"] == "COMPLETED"
        assert child["manifest"]["parent_run_id"] == "managed_smoke"
        assert comparison["base_run_id"] == "managed_smoke"
        assert len(child["history"]["runs"]) == 2


def test_bounded_real_session_smoke():
    with TemporaryDirectory() as directory:
        result = run_research_run_management(
            {
                "enabled": True,
                "base_output_directory": directory,
                "run_id": "real_smoke",
                "run_name": "real smoke",
                "prevent_overwrite": True,
            },
            {
                "enabled": True,
                "dry_run": False,
                "resume_enabled": True,
                "fail_fast": True,
                "continue_on_stage_failure": False,
                "global_task_budget": 20,
                "global_runtime_budget_seconds": 60,
                "smoke_mode": True,
                "enabled_stages": ["load_data", "optimization_search", "monte_carlo"],
            },
        )

        assert result["status"] == "COMPLETED"
        assert result["snapshot_index"]["config_count"] >= 1
        assert len(result["manifest"]["artifacts"]) == 5
        assert len(result["history"]["runs"]) == 1
        assert result["orchestrator_result"]["task_usage"] <= 20


if __name__ == "__main__":
    test_config_loading_and_disabled_behavior()
    test_run_id_generation_and_name_sanitization()
    test_invalid_run_id_rejects_path_traversal()
    test_collision_prevention()
    test_directory_creation_overwrite_and_resume_validation()
    test_config_snapshot_creation_and_hashing()
    test_missing_required_config_error_and_optional_handling()
    test_repository_metadata_fallback_and_environment_metadata()
    test_manifest_creation_schema_and_artifact_references()
    test_manifest_save_and_load()
    test_history_append_duplicate_update_and_corruption()
    test_comparison_with_same_changed_and_missing_metrics()
    test_reproducibility_success_dirty_partial_missing_snapshot_and_artifact_failure()
    test_run_summary_schema()
    test_dry_run_management_and_existing_orchestrator_compatibility()
    test_manager_with_fake_orchestrator_smoke_resume_and_parent_child()
    test_bounded_real_session_smoke()
    print("test_research_run_management passed")
