from src.research.frameworks.historical.campaign import CampaignControl, plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import CampaignStatus
from src.research.frameworks.historical.campaign.models import HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_cancellation_before_child_creates_no_child_run(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    control = CampaignControl(); control.cancel()
    result = run_historical_campaign(plan, {"local": binding}, cancellation_control=control)
    assert result.status is CampaignStatus.CANCELLED and result.completed_tasks == 0
    assert not (tmp_path / plan.campaign_id / "children").exists()


def test_campaign_pause_preserves_planned_child_boundary(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    control = CampaignControl(); control.pause()
    result = run_historical_campaign(plan, {"local": binding}, cancellation_control=control)
    assert result.status is CampaignStatus.PAUSED and result.completed_tasks == 0


def test_campaign_pause_after_child_preserves_last_valid_child_for_resume(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("a", start_row=0, end_row=20), HistoricalResearchRange("b", start_row=20, end_row=40)))
    plan = plan_historical_campaign(config, {"local": binding})
    paused = run_historical_campaign(plan, {"local": binding}, pause_after_tasks=1)
    assert paused.status is CampaignStatus.PAUSED and paused.completed_tasks == 1
    resumed = run_historical_campaign(plan, {"local": binding})
    assert resumed.status is CampaignStatus.COMPLETED and resumed.reused_tasks == 1
