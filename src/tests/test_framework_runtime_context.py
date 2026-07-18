from src.research.frameworks.alignment import build_causal_alignment
from src.research.frameworks.preparation import prepare_timeframe_data
from src.research.frameworks.profiling.runtime import FrameworkRuntimeContext
from src.research.frameworks.reporting import _configuration
from src.trading_frameworks.loader import load_trading_framework
from src.utils.trading_framework_performance import _context


def test_framework_runtime_context():
    configuration = _configuration("triple_screen_trading")
    framework = load_trading_framework(configuration.framework)
    prepared = prepare_timeframe_data(configuration, framework, _context(configuration.framework, 80).frames)
    alignment = build_causal_alignment(prepared, configuration.primary_role)
    first = FrameworkRuntimeContext.build(configuration, prepared, alignment)
    second = FrameworkRuntimeContext.build(configuration, prepared, alignment)
    assert first.summary() == second.summary() and first.row_count == 80


if __name__ == "__main__":
    test_framework_runtime_context(); print("test_framework_runtime_context passed")
