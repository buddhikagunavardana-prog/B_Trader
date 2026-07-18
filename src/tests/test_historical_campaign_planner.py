from pathlib import Path

import pytest

from src.research.frameworks.historical.campaign import plan_historical_campaign
from src.research.frameworks.historical.campaign.models import HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_plan_is_side_effect_free_and_records_reason(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 45)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("first", start_row=0, end_row=20), HistoricalResearchRange("second", start_row=20, end_row=45)))
    plan = plan_historical_campaign(config, {"local": binding})
    assert len(plan.tasks) == 2
    assert all("ema_ribbon_trend x local" in task.reason for task in plan.tasks)
    assert not Path(tmp_path, plan.campaign_id).exists()


def test_campaign_planner_rejects_duplicate_canonical_tasks(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    duplicate = HistoricalResearchRange("same", start_row=0, end_row=20)
    config = campaign_config(tmp_path, ranges=(duplicate, duplicate))
    with pytest.raises(ValueError, match="duplicate canonical tasks"):
        plan_historical_campaign(config, {"local": binding})


def test_campaign_planner_rejects_missing_source_binding(tmp_path):
    config = campaign_config(tmp_path)
    with pytest.raises(ValueError, match="source-set bindings differ"):
        plan_historical_campaign(config, {})
