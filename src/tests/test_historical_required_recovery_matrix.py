import json
import shutil
import tempfile
from pathlib import Path

from src.research.frameworks.historical.exceptions import (
    CodeMismatchError,
    ConfigurationMismatchError,
    InvalidChunkPlanError,
)
from src.research.frameworks.historical.recovery import (
    load_plan,
    recover_historical_run,
    resume_historical_research,
)
from src.research.frameworks.historical.integrity import validate_historical_run
from src.tests.historical_test_data import historical_case


def _expect(error_type, operation):
    try:
        operation()
    except error_type:
        return
    raise AssertionError(f"{error_type.__name__} was not raised")


def _write_json(path, payload):
    Path(path).write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def test_historical_required_recovery_matrix():
    with tempfile.TemporaryDirectory() as root:
        plan, result, _, _, _, sources = historical_case("ema_ribbon_trend", 120, 40, root)
        run = Path(result.run_directory)

        # A stale manifest must not hide valid durable checkpoints.
        manifest_path = run / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update(status="running", completed_chunks=[], continuity_frontier=-1)
        _write_json(manifest_path, manifest)
        validation = validate_historical_run(run, plan, strict=False)
        assert not validation["valid"] and "manifest_completed_chunks" in validation["manifest_errors"]
        resumed = resume_historical_research(run, sources)
        assert resumed.completed_chunks == 3
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "completed"

        # An artifact without a checkpoint and a temporary write are invalidated
        # from the earliest broken continuity point.
        missing_checkpoint = run / "chunks/chunk_000001/checkpoint.json"
        missing_checkpoint.unlink()
        temporary = run / "chunks/chunk_000001/decisions.csv.gz.tmp"
        temporary.write_text("partial", encoding="utf-8")
        report = recover_historical_run(run, plan)
        assert report.retained_chunks == (plan.chunks[0].chunk_id,)
        assert report.chunks_to_rerun == tuple(chunk.chunk_id for chunk in plan.chunks[1:])
        assert report.orphan_files and not temporary.exists()

    with tempfile.TemporaryDirectory() as root:
        plan, result, _, _, _, _ = historical_case("ema_ribbon_trend", 120, 40, root)
        run = Path(result.run_directory)
        checkpoint = run / "chunks/chunk_000001/checkpoint.json"
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        payload["predecessor_final_state_fingerprint"] = "changed"
        _write_json(checkpoint, payload)
        report = recover_historical_run(run, plan)
        assert len(report.retained_chunks) == 1 and len(report.chunks_to_rerun) == 2

    with tempfile.TemporaryDirectory() as root:
        _, result, _, _, _, sources = historical_case("ema_ribbon_trend", 80, 40, root)
        run = Path(result.run_directory)
        plan_path = run / "plan.json"
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        payload["run_configuration"]["maximum_memory_bytes"] += 1
        _write_json(plan_path, payload)
        _expect(ConfigurationMismatchError, lambda: load_plan(run))

        payload["run_configuration"]["maximum_memory_bytes"] -= 1
        payload["code_fingerprint"] = "changed-code"
        _write_json(plan_path, payload)
        _expect(CodeMismatchError, lambda: resume_historical_research(run, sources))

    # Stored plans reject gaps, overlaps, and out-of-order chunks before merge.
    with tempfile.TemporaryDirectory() as root:
        _, result, _, _, _, _ = historical_case("ema_ribbon_trend", 120, 40, root)
        original = Path(result.run_directory)
        for scenario in ("gap", "overlap", "out_of_order"):
            copied = Path(root) / scenario
            shutil.copytree(original, copied)
            plan_path = copied / "plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            if scenario == "gap":
                payload["chunks"][1]["logical_start"] += 1
            elif scenario == "overlap":
                payload["chunks"][1]["logical_start"] -= 1
            else:
                payload["chunks"][1], payload["chunks"][2] = payload["chunks"][2], payload["chunks"][1]
            _write_json(plan_path, payload)
            _expect(InvalidChunkPlanError, lambda copied=copied: load_plan(copied))


if __name__ == "__main__":
    test_historical_required_recovery_matrix()
    print("test_historical_required_recovery_matrix passed")
