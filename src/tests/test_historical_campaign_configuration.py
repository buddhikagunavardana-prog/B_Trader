import json

import pytest

from src.research.frameworks.historical.campaign.configuration import (
    campaign_configuration_from_dict,
    load_campaign_configuration,
)


def test_portable_campaign_configurations_load():
    smoke = load_campaign_configuration("src/config/framework_research/historical/campaigns/structural_smoke.json")
    all_50 = load_campaign_configuration("src/config/framework_research/historical/campaigns/structural_all_50.json")
    assert smoke.concurrency == all_50.concurrency == 1
    assert all_50.framework_configuration_names == ("all",)
    assert all_50.output_root == "reports/historical_campaigns"


def test_campaign_configuration_rejects_unknown_fields(tmp_path):
    with pytest.raises(ValueError, match="unknown campaign configuration fields"):
        campaign_configuration_from_dict({"campaign_name": "x", "unknown": True})
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_campaign_configuration(path)
