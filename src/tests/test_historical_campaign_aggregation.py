from dataclasses import replace
import json
from pathlib import Path

from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.aggregation import aggregate_campaign_results
from src.research.frameworks.historical.campaign.models import HistoricalCampaignTaskResult
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_structural_aggregate_is_deterministic_and_follows_task_order(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    stored = result.aggregate
    result_path = Path(result.campaign_directory) / "task_results" / f"{plan.tasks[0].task_id}.json"
    repeated = aggregate_campaign_results(
        plan,
        [HistoricalCampaignTaskResult.from_dict(json.loads(result_path.read_text(encoding="utf-8")))],
    )
    assert stored.aggregate_fingerprint == repeated.aggregate_fingerprint
    assert [row["task_id"] for row in stored.task_rows] == [task.task_id for task in plan.tasks]


def test_aggregate_fingerprint_changes_with_contributing_structural_result(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    result_path = Path(result.campaign_directory) / "task_results" / f"{plan.tasks[0].task_id}.json"
    row = HistoricalCampaignTaskResult.from_dict(json.loads(result_path.read_text(encoding="utf-8")))
    changed = replace(row, warning_count=row.warning_count + 1)
    assert aggregate_campaign_results(plan, [changed]).aggregate_fingerprint != result.aggregate.aggregate_fingerprint
