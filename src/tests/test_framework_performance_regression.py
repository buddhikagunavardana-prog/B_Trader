from src.research.frameworks.profiling.models import ExecutionMode
from src.research.frameworks.profiling.profiler import profile_framework
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_performance_regression():
    name = "opening_range_breakout"
    result = profile_framework(_configuration(name), _context(name, 1000).frames, ExecutionMode.STATEFUL_POLICY, 1, 2)
    assert result.repeated_indicator_calculations == 0 and result.median_ms < 744.1556533


if __name__ == "__main__":
    test_framework_performance_regression(); print("test_framework_performance_regression passed")
