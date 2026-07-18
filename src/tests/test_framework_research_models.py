import json

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.models import OutputMode, PreparationMode
from src.tests.framework_research_test_data import precomputed_data, research_configuration


def test_models_and_result_are_json_serializable():
    config = research_configuration("turtle_trading")
    assert config.run_id == research_configuration("turtle_trading").run_id
    assert config.output_mode is OutputMode.DATAFRAME
    assert config.preparation_mode is PreparationMode.PRECOMPUTED_ONLY
    result = run_framework_decision_series(config, precomputed_data("turtle_trading"))
    json.dumps(config.to_dict()); json.dumps(result.to_dict())
    assert result.rows_evaluated + result.rows_skipped == len(result.decisions)


if __name__ == "__main__":
    test_models_and_result_are_json_serializable(); print("test_framework_research_models passed")
