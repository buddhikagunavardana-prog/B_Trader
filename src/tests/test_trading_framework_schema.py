import json

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import ParameterDefinition, ParameterType
from src.trading_frameworks.registry import trading_framework_registry


def test_all_framework_schemas_are_gui_serializable_and_documented():
    for definition in trading_framework_registry.list_definitions():
        json.dumps(definition)
        schema = definition["schema"]
        assert schema["entry_logic"] and schema["exit_logic"] and schema["risk_logic"]
        assert schema["causal_contract"]
        assert all(item["description"] for item in schema["parameters"])


def test_parameter_types_reject_ambiguous_and_out_of_range_values():
    period = ParameterDefinition("period", ParameterType.PERIOD, 20, "lookback")
    percentage = ParameterDefinition("risk", ParameterType.PERCENTAGE, 0.01, "risk", 0, 0.1)
    for value in (True, 0, -1):
        try:
            period.validate(value)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid period accepted: {value}")
    assert percentage.validate(0.05) == 0.05


def test_abstract_base_cannot_be_instantiated():
    try:
        BaseTradingFramework()
    except TypeError:
        pass
    else:
        raise AssertionError("abstract framework base was instantiated")


if __name__ == "__main__":
    test_all_framework_schemas_are_gui_serializable_and_documented()
    test_parameter_types_reject_ambiguous_and_out_of_range_values()
    test_abstract_base_cannot_be_instantiated()
    print("test_trading_framework_schema passed")
