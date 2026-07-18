from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.profiling.memory import result_memory
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_memory_behavior():
    configuration = _configuration("opening_range_breakout")
    samples = []
    for rows in (100, 1000):
        source = _context(configuration.framework, rows).frames
        samples.append(result_memory(run_framework_decision_series(configuration, source), source)["estimated_total_bytes"])
    assert 1 < samples[1] / samples[0] < 15


if __name__ == "__main__":
    test_framework_memory_behavior(); print("test_framework_memory_behavior passed")
