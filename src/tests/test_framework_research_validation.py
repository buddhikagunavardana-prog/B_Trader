import pandas as pd

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.validator import validate_decision_series, validate_repeatability
from src.tests.framework_research_test_data import precomputed_data, research_configuration


def test_output_validation_repeatability_and_skip_reasons():
    config = research_configuration("ichimoku_cloud_trading")
    first = run_framework_decision_series(config, precomputed_data("ichimoku_cloud_trading"))
    second = run_framework_decision_series(config, precomputed_data("ichimoku_cloud_trading"))
    assert validate_repeatability(first.decisions, second.decisions).valid
    assert validate_decision_series(first.decisions).valid
    skipped = first.decisions[~first.decisions["decision_valid"]]
    assert skipped["skip_reason"].str.len().gt(0).all()
    broken = first.decisions.drop(columns=["signal"])
    assert not validate_decision_series(broken).valid


if __name__ == "__main__":
    test_output_validation_repeatability_and_skip_reasons(); print("test_framework_research_validation passed")
