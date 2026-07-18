from pathlib import Path

import pytest

from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign, validate_campaign
from src.research.frameworks.historical.campaign.integrity import CampaignIntegrityError
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_integrity_accepts_complete_campaign_and_rejects_corrupt_child(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path, chunk_size_rows=15), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    assert validate_campaign(result.campaign_directory, plan, {"local": binding})["valid"]
    artifact = next(Path(result.campaign_directory).glob("children/*/chunks/chunk_*/decisions.csv.gz"))
    with artifact.open("ab") as handle:
        handle.write(b"corrupt")
    with pytest.raises(CampaignIntegrityError):
        validate_campaign(result.campaign_directory, plan, {"local": binding})


def test_campaign_integrity_rejects_changed_plan_fingerprint(tmp_path):
    from dataclasses import replace
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    changed = replace(plan, plan_fingerprint="changed")
    with pytest.raises(CampaignIntegrityError):
        validate_campaign(result.campaign_directory, changed, {"local": binding})


def test_campaign_integrity_rejects_unsupported_stored_manifest_version(tmp_path):
    import json
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    result = run_historical_campaign(plan, {"local": binding})
    manifest = Path(result.campaign_directory) / "campaign_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8")); payload["manifest_schema_version"] = "99"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CampaignIntegrityError):
        validate_campaign(result.campaign_directory, plan, {"local": binding})
