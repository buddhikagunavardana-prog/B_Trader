import pytest

from src.research.frameworks.historical.campaign.models import (
    CampaignFailurePolicy,
    HistoricalCampaignConfig,
    HistoricalResearchRange,
)


def test_campaign_models_validate_ranges_and_serial_execution(tmp_path):
    config = HistoricalCampaignConfig(
        "campaign", ("ema_ribbon_trend",), ("local",),
        (HistoricalResearchRange("rows", start_row=0, end_row=10),),
        output_root=str(tmp_path), failure_policy=CampaignFailurePolicy.FAIL_FAST,
    )
    assert config.concurrency == 1 and config.identity_snapshot()["failure_policy"] == "fail_fast"
    with pytest.raises(ValueError, match="exactly 1"):
        HistoricalCampaignConfig("campaign", ("ema_ribbon_trend",), ("local",), (HistoricalResearchRange("full"),), concurrency=2)
    with pytest.raises(ValueError, match="cannot mix"):
        HistoricalResearchRange("mixed", start_row=0, start_timestamp="2026-01-01")


def test_campaign_models_reject_empty_and_unsafe_values():
    with pytest.raises(ValueError):
        HistoricalCampaignConfig("../escape", ("x",), ("local",), (HistoricalResearchRange("full"),))
    with pytest.raises(ValueError, match="must not be empty"):
        HistoricalCampaignConfig("campaign", (), ("local",), (HistoricalResearchRange("full"),))
    with pytest.raises(ValueError, match="unsupported campaign manifest"):
        HistoricalCampaignConfig("campaign", ("x",), ("local",), (HistoricalResearchRange("full"),), manifest_schema_version="99")
