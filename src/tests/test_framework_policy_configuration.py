from dataclasses import replace
from src.research.frameworks.configuration import validate_research_configuration
from src.research.frameworks.exceptions import ResearchConfigurationError
from src.tests.framework_expansion_test_data import config


def test_old_configuration_loads_and_new_fields_validate():
    original = config("ema_ribbon_trend")
    assert validate_research_configuration(original).opposite_signal_mode == "request_exit"
    for changed in (replace(original, opposite_signal_mode="unsafe"), replace(original, max_hold_enforcement=True, max_hold_bars=None), replace(original, max_hold_duration="later"), replace(original, session_configuration={"unknown": True})):
        try:
            validate_research_configuration(changed)
        except ResearchConfigurationError:
            pass
        else:
            raise AssertionError("invalid policy configuration was accepted")


if __name__ == "__main__":
    test_old_configuration_loads_and_new_fields_validate(); print("test_framework_policy_configuration passed")
