from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_multi_timeframe_campaign_preserves_explicit_completed_bar_bundle(tmp_path):
    binding = binding_for("multi", "triple_screen_trading", 60)
    config = campaign_config(tmp_path, framework="triple_screen_trading", source_name="multi", chunk_size_rows=30)
    plan = plan_historical_campaign(config, {"multi": binding})
    result = run_historical_campaign(plan, {"multi": binding})
    task = plan.tasks[0]
    assert task.source_schema_fingerprints.keys() == binding.sources.keys()
    assert binding.completed_bar_alignment and result.status.value == "completed"
    assert result.aggregate.logical_row_count == 60
