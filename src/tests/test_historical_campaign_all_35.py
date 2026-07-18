from dataclasses import replace

from src.research.frameworks.historical.campaign import load_campaign_configuration, plan_historical_campaign
from src.tests.historical_campaign_test_data import all_35_bindings
from src.trading_frameworks.registry import trading_framework_registry


def test_all_35_registry_configurations_plan_without_fixed_campaign_count(tmp_path):
    config = load_campaign_configuration("src/config/framework_research/historical/campaigns/structural_all_35.json")
    config = replace(config, output_root=str(tmp_path))
    bindings = all_35_bindings(20)
    plan = plan_historical_campaign(config, bindings)
    assert len(trading_framework_registry.list_names()) == 35
    assert len(plan.tasks) == len(trading_framework_registry.list_names())
    assert {task.framework_name for task in plan.tasks} == set(trading_framework_registry.list_names())
