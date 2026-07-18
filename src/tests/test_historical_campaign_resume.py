from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import CampaignStatus, HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_completed_children_are_reused_on_resume(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    first = run_historical_campaign(plan, {"local": binding})
    second = run_historical_campaign(plan, {"local": binding})
    assert first.status is second.status is CampaignStatus.COMPLETED
    assert second.reused_tasks == 1


def test_cancelled_between_tasks_resumes_without_recomputing_valid_child(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("a", start_row=0, end_row=20), HistoricalResearchRange("b", start_row=20, end_row=40)))
    plan = plan_historical_campaign(config, {"local": binding})
    interrupted = run_historical_campaign(plan, {"local": binding}, stop_after_tasks=1)
    assert interrupted.status is CampaignStatus.CANCELLED
    resumed = run_historical_campaign(plan, {"local": binding})
    assert resumed.status is CampaignStatus.COMPLETED
    assert resumed.reused_tasks == 1 and resumed.completed_tasks == 2
