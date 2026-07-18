from dataclasses import replace
from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_profiling_runtime():
    configuration = replace(_configuration("ema_ribbon_trend"), enable_controller_timing=True, run_id=None)
    result = run_framework_decision_series(configuration, _context(configuration.framework, 80).frames)
    runtime = result.reproducibility["runtime_context"]
    assert runtime["row_count"] == 80 and runtime["instrumentation_enabled"]
    assert result.reproducibility["diagnostics_seconds"] >= 0
    assert result.reproducibility["normalization_seconds"] >= 0


if __name__ == "__main__":
    test_framework_profiling_runtime(); print("test_framework_profiling_runtime passed")
