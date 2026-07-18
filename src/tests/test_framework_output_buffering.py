from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.reporting import _configuration
from src.research.frameworks.validator import DECISION_COLUMNS, STATE_COLUMNS
from src.utils.trading_framework_performance import _context


def test_framework_output_buffering():
    configuration = _configuration("triple_screen_trading")
    result = run_framework_decision_series(configuration, _context(configuration.framework, 120).frames)
    assert list(result.decisions.columns) == list(DECISION_COLUMNS + STATE_COLUMNS)
    assert result.decisions.index.equals(result.decisions.index.copy())


if __name__ == "__main__":
    test_framework_output_buffering(); print("test_framework_output_buffering passed")
