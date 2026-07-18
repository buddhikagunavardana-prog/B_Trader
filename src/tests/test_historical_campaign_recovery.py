import json
from pathlib import Path

from src.research.frameworks.historical.campaign import plan_historical_campaign, recover_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_recovery_retains_unaffected_child_and_invalidates_only_corrupt_task(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("a", start_row=0, end_row=20), HistoricalResearchRange("b", start_row=20, end_row=40)), chunk_size_rows=10)
    plan = plan_historical_campaign(config, {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    corrupt_task = plan.tasks[0]
    artifact = next((Path(result.campaign_directory) / "children" / corrupt_task.child_run_id).glob("chunks/chunk_*/decisions.csv.gz"))
    artifact.unlink()
    report = recover_historical_campaign(result.campaign_directory, plan, {"local": binding})
    assert report.invalidated_tasks == (corrupt_task.task_id,)
    assert plan.tasks[1].task_id in report.retained_tasks
    assert len(report.tasks_to_rerun) == 1
    resumed = run_historical_campaign(plan, {"local": binding})
    assert resumed.status.value == "completed" and resumed.reused_tasks == 1


def test_campaign_recovery_reports_orphans_and_stale_summary(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    root = Path(result.campaign_directory)
    orphan = root / "children" / "orphan_child"; orphan.mkdir(parents=True)
    summary = root / "summaries" / "structural_summary_manifest.json"
    payload = json.loads(summary.read_text(encoding="utf-8")); payload["aggregate_fingerprint"] = "stale"
    summary.write_text(json.dumps(payload), encoding="utf-8")
    report = recover_historical_campaign(root, plan, {"local": binding})
    assert any("orphan_child" in item for item in report.orphan_files)
    assert report.stale_summaries


def test_task_result_is_reused_when_campaign_manifest_is_stale(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    manifest = Path(result.campaign_directory) / "campaign_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["task_results"] = {}; payload["task_statuses"] = {}
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    resumed = run_historical_campaign(plan, {"local": binding})
    assert resumed.status.value == "completed" and resumed.reused_tasks == 1
