import json

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.validator import DECISION_COLUMNS,STATE_COLUMNS
from src.tests.framework_research_test_data import precomputed_data, research_configuration, synthetic_scenarios
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.exceptions import FrameworkDataError
from src.trading_frameworks.models import FrameworkContext


def test_all_five_frameworks_generate_normalized_chronological_series():
    for name in ("triple_screen_trading","turtle_trading","ichimoku_cloud_trading","bollinger_mean_reversion","donchian_breakout"):
        result = run_framework_decision_series(research_configuration(name), precomputed_data(name, 100))
        assert tuple(result.decisions.columns) == DECISION_COLUMNS+STATE_COLUMNS
        assert result.decisions["timestamp"].is_monotonic_increasing
        assert result.validation.valid, (name, result.validation.to_dict())
        assert not ({"pnl", "roi", "win_rate", "profit_factor", "drawdown", "sharpe", "balance"} & set(result.summary))
        for column in ("diagnostics", "warnings", "rows_available"):
            result.decisions[column].map(json.loads)


def test_named_synthetic_scenario_fixture_coverage():
    scenarios = synthetic_scenarios()
    assert set(scenarios) == {
        "strong_uptrend", "strong_downtrend", "sideways_range", "volatility_breakout",
        "false_breakout", "bullish_pullback", "bearish_rally", "sparse_higher_timeframe",
        "missing_bar_gap", "short_warmup",
    }
    assert len(scenarios["sparse_higher_timeframe"]) < len(scenarios["strong_uptrend"])
    assert len(scenarios["missing_bar_gap"]) < len(scenarios["strong_uptrend"])


def test_prepared_execution_rejects_future_rows():
    data = precomputed_data("turtle_trading")
    try:
        load_trading_framework("turtle").execute_prepared(
            FrameworkContext(data), data["execution"].index[-2],
        )
    except FrameworkDataError as error:
        assert "future" in str(error)
    else:
        raise AssertionError("prepared execution accepted a future row")


if __name__ == "__main__":
    test_all_five_frameworks_generate_normalized_chronological_series(); test_named_synthetic_scenario_fixture_coverage(); test_prepared_execution_rejects_future_rows(); print("test_framework_decision_series passed")
