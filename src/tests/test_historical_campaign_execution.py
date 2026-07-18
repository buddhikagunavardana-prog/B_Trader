from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import CampaignStatus, HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_executes_children_serially_and_delegates_to_phase_24_8(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("a", start_row=0, end_row=20), HistoricalResearchRange("b", start_row=20, end_row=40)), chunk_size_rows=10)
    plan = plan_historical_campaign(config, {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    assert result.status is CampaignStatus.COMPLETED
    assert result.completed_tasks == 2 and result.aggregate.chunk_count == 4
    for task in plan.tasks:
        child = tmp_path / plan.campaign_id / "children" / task.child_run_id
        assert (child / "plan.json").is_file() and (child / "manifest.json").is_file()
        assert (child / "merge_manifest.json").is_file()


def test_campaign_execution_rejects_changed_runtime_source_set(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    changed = binding_for("local", "ema_ribbon_trend", 31)
    try:
        run_historical_campaign(plan, {"local": changed})
    except ValueError as error:
        assert "fingerprint changed" in str(error)
    else:
        raise AssertionError("changed source set was accepted")
