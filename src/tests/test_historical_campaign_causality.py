import pandas as pd
from pathlib import Path

from src.research.frameworks.historical.campaign import HistoricalSourceSetBinding, plan_historical_campaign, run_historical_campaign
from src.research.frameworks.historical.source import source_bundle
from src.tests.historical_campaign_test_data import binding_for, campaign_config
from src.utils.trading_framework_performance import _context


def test_campaign_future_change_invariance_before_chunk_boundary(tmp_path):
    frames = {role: frame.copy(deep=True) for role, frame in _context("ema_ribbon_trend", 50).frames.items()}
    changed = {role: frame.copy(deep=True) for role, frame in frames.items()}
    changed["execution"].iloc[35:, changed["execution"].columns.get_loc("close")] += 1000
    first = HistoricalSourceSetBinding("local", "15m", {"execution": "15m"}, source_bundle(frames), applicable_frameworks=("ema_ribbon_trend",))
    second = HistoricalSourceSetBinding("local", "15m", {"execution": "15m"}, source_bundle(changed), applicable_frameworks=("ema_ribbon_trend",))
    plan_a = plan_historical_campaign(campaign_config(tmp_path / "a", chunk_size_rows=20), {"local": first})
    plan_b = plan_historical_campaign(campaign_config(tmp_path / "b", chunk_size_rows=20), {"local": second})
    result_a = run_historical_campaign(plan_a, {"local": first})
    result_b = run_historical_campaign(plan_b, {"local": second})
    path_a = Path(result_a.campaign_directory) / "children" / plan_a.tasks[0].child_run_id / "merged_decisions.csv"
    path_b = Path(result_b.campaign_directory) / "children" / plan_b.tasks[0].child_run_id / "merged_decisions.csv"
    left = pd.read_csv(path_a).iloc[:35].reset_index(drop=True)
    right = pd.read_csv(path_b).iloc[:35].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)
