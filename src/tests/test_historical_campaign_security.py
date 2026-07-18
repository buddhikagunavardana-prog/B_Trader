import pytest

from src.research.frameworks.historical.campaign.models import HistoricalSourceSetBinding, safe_campaign_directory
from src.tests.historical_campaign_test_data import binding_for


@pytest.mark.parametrize("identity", ["../escape", "a/b", "a\\b", ".."])
def test_campaign_path_traversal_is_rejected(tmp_path, identity):
    with pytest.raises(ValueError):
        safe_campaign_directory(tmp_path, identity)


def test_source_location_is_absent_from_deterministic_source_identity():
    binding = binding_for("local", "ema_ribbon_trend", 20)
    snapshot = binding.identity_snapshot()
    assert all("location" not in descriptor for descriptor in snapshot["sources"].values())


def test_unsafe_source_set_name_is_rejected():
    base = binding_for("local", "ema_ribbon_trend", 20)
    with pytest.raises(ValueError):
        HistoricalSourceSetBinding("../escape", base.execution_timeframe, base.role_timeframes, base.sources)
