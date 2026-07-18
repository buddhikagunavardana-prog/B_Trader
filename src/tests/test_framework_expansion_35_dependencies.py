from dataclasses import replace
from src.research.frameworks.models import PreparationMode
from src.research.frameworks.preparation import prepare_timeframe_data
from src.tests.framework_expansion_35_test_data import NEW_15
from src.tests.framework_expansion_test_data import config, data
from src.trading_frameworks.loader import load_trading_framework


def test_compute_missing_dependencies_are_deterministic_and_non_mutating():
    for name in NEW_15:
        rows = 700 if name == "pivot_range_breakout" else 240
        configuration = replace(config(name), preparation_mode=PreparationMode.COMPUTE_MISSING)
        source = data(name, rows)["execution"][["open", "high", "low", "close", "volume"]].copy()
        snapshot = source.copy(deep=True); framework = load_trading_framework(name)
        first = prepare_timeframe_data(configuration, framework, {"execution": source})["execution"]
        second = prepare_timeframe_data(configuration, framework, {"execution": source})["execution"]
        assert source.equals(snapshot), name
        assert first.frame.equals(second.frame), name
        assert set(framework.schema.required_columns_by_role["execution"]).issubset(first.frame.columns), name
        assert len(first.metadata["dependency_request_fingerprints"]) == len(set(first.metadata["dependency_request_fingerprints"])), name


if __name__ == "__main__":
    test_compute_missing_dependencies_are_deterministic_and_non_mutating(); print("test_framework_expansion_35_dependencies passed")
