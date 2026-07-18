from src.research.frameworks.historical.campaign import plan_historical_campaign
from src.research.frameworks.historical.campaign.models import HistoricalSourceSetBinding
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_and_task_identities_ignore_mapping_insertion_order(tmp_path):
    first = binding_for("local", "triple_screen_trading", 30)
    reversed_roles = dict(reversed(list(first.role_timeframes.items())))
    reversed_sources = dict(reversed(list(first.sources.items())))
    second = HistoricalSourceSetBinding("local", first.execution_timeframe, reversed_roles, reversed_sources, applicable_frameworks=("triple_screen_trading",))
    config = campaign_config(tmp_path, framework="triple_screen_trading")
    plan_a = plan_historical_campaign(config, {"local": first})
    plan_b = plan_historical_campaign(config, {"local": second})
    assert plan_a.campaign_id == plan_b.campaign_id
    assert [task.task_id for task in plan_a.tasks] == [task.task_id for task in plan_b.tasks]


def test_output_root_does_not_enter_deterministic_identity(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    first = plan_historical_campaign(campaign_config(tmp_path / "one"), {"local": binding})
    second = plan_historical_campaign(campaign_config(tmp_path / "two"), {"local": binding})
    assert first.campaign_id == second.campaign_id
    assert first.tasks[0].task_id == second.tasks[0].task_id
