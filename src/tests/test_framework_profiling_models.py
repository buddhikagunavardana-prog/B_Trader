from src.research.frameworks.profiling.aggregation import timing_statistics
from src.research.frameworks.profiling.models import DiagnosticLevel, PerformanceBudget, SnapshotMode


def test_framework_profiling_models():
    values = timing_statistics([.001, .002, .003, .004, .005])
    assert values["median_ms"] == 3.0 and values["p90_ms"] == 4.6
    assert DiagnosticLevel.STANDARD.value == "standard"
    assert SnapshotMode.TRANSITIONS_ONLY.value == "transitions_only"
    assert PerformanceBudget().maximum_scaling_ratio == 12.0


if __name__ == "__main__":
    test_framework_profiling_models(); print("test_framework_profiling_models passed")
