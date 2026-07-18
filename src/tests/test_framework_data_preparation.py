import pandas as pd

from src.research.frameworks.exceptions import ResearchPreparationError
from src.research.frameworks.models import PreparationMode
from src.research.frameworks.preparation import prepare_timeframe_data
from src.tests.framework_research_test_data import precomputed_data, raw_data, research_configuration
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.registry import trading_framework_registry


def test_precomputed_only_preserves_sources_and_rejects_missing_columns():
    data = precomputed_data("turtle_trading"); before = data["execution"].copy(deep=True)
    prepared = prepare_timeframe_data(research_configuration("turtle_trading"), load_trading_framework("turtle"), data)
    pd.testing.assert_frame_equal(data["execution"], before, check_exact=True)
    assert prepared["execution"].metadata["timezone"] == "UTC"
    missing = {"execution": before.drop(columns=["ATR"])}
    try: prepare_timeframe_data(research_configuration("turtle_trading"), load_trading_framework("turtle"), missing)
    except ResearchPreparationError as error: assert "ATR" in str(error)
    else: raise AssertionError("missing precomputed data accepted")


def test_compute_missing_mode_is_deterministic_for_all_frameworks():
    for name in ("triple_screen_trading","turtle_trading","ichimoku_cloud_trading","bollinger_mean_reversion","donchian_breakout"):
        config = research_configuration(name, PreparationMode.COMPUTE_MISSING)
        framework = load_trading_framework(name); data = raw_data(name)
        first = prepare_timeframe_data(config, framework, data); second = prepare_timeframe_data(config, framework, data)
        for role in first:
            pd.testing.assert_frame_equal(first[role].frame, second[role].frame, check_exact=True)
            assert first[role].precomputed_indicator_columns


if __name__ == "__main__":
    test_precomputed_only_preserves_sources_and_rejects_missing_columns(); test_compute_missing_mode_is_deterministic_for_all_frameworks(); print("test_framework_data_preparation passed")
