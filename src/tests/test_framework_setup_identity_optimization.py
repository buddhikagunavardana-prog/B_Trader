from dataclasses import replace
from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_setup_identity_optimization():
    for name in ("opening_range_breakout", "nr4_nr7_volatility_breakout", "pin_bar_rejection", "pivot_range_breakout"):
        configuration = replace(_configuration(name), run_id=None)
        source = _context(name, 160).frames
        first = run_framework_decision_series(configuration, source).decisions["setup_id"]
        second = run_framework_decision_series(configuration, source).decisions["setup_id"]
        assert first.equals(second)


if __name__ == "__main__":
    test_framework_setup_identity_optimization(); print("test_framework_setup_identity_optimization passed")
