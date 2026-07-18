import pytest
import json
from pathlib import Path

from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import HistoricalResearchRange
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_records_one_active_child_and_bounded_child_memory(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 40)
    config = campaign_config(tmp_path, ranges=(HistoricalResearchRange("a", start_row=0, end_row=20), HistoricalResearchRange("b", start_row=20, end_row=40)), chunk_size_rows=10)
    plan = plan_historical_campaign(config, {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    manifest = json.loads((Path(result.campaign_directory) / "campaign_manifest.json").read_text(encoding="utf-8"))
    assert manifest["memory_diagnostics"]["active_child_limit"] == 1
    assert manifest["memory_diagnostics"]["maximum_child_input_bytes"] < config.maximum_memory_bytes


def test_child_memory_contract_failure_is_not_silently_replanned(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    config = campaign_config(tmp_path, maximum_memory_bytes=1)
    plan = plan_historical_campaign(config, {"local": binding})
    with pytest.raises(MemoryError):
        run_historical_campaign(plan, {"local": binding})
