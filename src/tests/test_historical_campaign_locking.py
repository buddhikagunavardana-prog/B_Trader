import os
import time

import pytest

from src.research.frameworks.historical.campaign import plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.campaign.models import safe_campaign_directory
from src.research.frameworks.historical.exceptions import LockAcquisitionError
from src.research.frameworks.historical.locking import ChunkLock
from src.tests.historical_campaign_test_data import binding_for, campaign_config


def test_campaign_lock_rejects_concurrent_owner_and_recovers_stale_lock(tmp_path):
    binding = binding_for("local", "ema_ribbon_trend", 30)
    plan = plan_historical_campaign(campaign_config(tmp_path), {"local": binding})
    root = safe_campaign_directory(tmp_path, plan.campaign_id); root.mkdir(parents=True)
    lock = ChunkLock(root / "campaign.lock").acquire()
    try:
        with pytest.raises(LockAcquisitionError):
            run_historical_campaign(plan, {"local": binding})
    finally:
        lock.release()
    (root / "campaign.lock").write_text("stale", encoding="utf-8")
    old = time.time() - 100
    os.utime(root / "campaign.lock", (old, old))
    result = run_historical_campaign(plan, {"local": binding}, stale_lock_timeout_seconds=1)
    assert result.status.value == "completed" and not (root / "campaign.lock").exists()
