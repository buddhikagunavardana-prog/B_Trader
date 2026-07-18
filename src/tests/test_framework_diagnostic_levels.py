from dataclasses import replace
from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def test_framework_diagnostic_levels():
    configuration = _configuration("stochastic_pullback_trend")
    source = _context(configuration.framework, 160).frames
    outputs = [run_framework_decision_series(replace(configuration, state_diagnostics_level=level, run_id=None), source).decisions for level in ("none", "summary", "standard", "full")]
    stable = [column for column in outputs[0].columns if column not in {"diagnostics", "controller_time_ns", "policy_time_ns"}]
    assert all(outputs[0][stable].equals(candidate[stable]) for candidate in outputs[1:])
    assert outputs[0]["diagnostics"].eq("{}").all()


if __name__ == "__main__":
    test_framework_diagnostic_levels(); print("test_framework_diagnostic_levels passed")
