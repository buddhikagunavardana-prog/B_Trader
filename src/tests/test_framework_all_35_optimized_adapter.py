from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context


def test_framework_all_35_optimized_adapter():
    names = trading_framework_registry.list_names()
    assert len(names) == 35
    for name in names:
        source = _context(name, 80).frames
        before = {role: frame.copy(deep=True) for role, frame in source.items()}
        result = run_framework_decision_series(_configuration(name), source)
        assert result.validation.valid and len(result.decisions) == 80
        assert all(source[role].equals(frame) for role, frame in before.items())
        assert result.reproducibility["repeated_indicator_calculation_count"] == 0


if __name__ == "__main__":
    test_framework_all_35_optimized_adapter(); print("test_framework_all_35_optimized_adapter passed")
