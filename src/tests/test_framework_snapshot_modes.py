from dataclasses import replace
from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_snapshot_modes():
    configuration = _configuration("nr4_nr7_volatility_breakout")
    source = _context(configuration.framework, 160).frames
    results = [run_framework_decision_series(replace(configuration, persist_state_snapshots=mode, run_id=None), source) for mode in (False, "final_only", "transitions_only", "full")]
    assert all(results[0].decisions.equals(candidate.decisions) for candidate in results[1:])
    counts = [candidate.reproducibility["final_policy_state_summary"]["stored_snapshot_count"] for candidate in results]
    assert counts[0] == 0 and counts[-1] > counts[2] >= counts[1]


if __name__ == "__main__":
    test_framework_snapshot_modes(); print("test_framework_snapshot_modes passed")
