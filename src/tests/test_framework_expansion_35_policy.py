from src.research.frameworks.state.policies import framework_policy_requirements
from src.tests.framework_expansion_35_test_data import NEW_15
from src.trading_frameworks.loader import load_trading_framework


def test_new_framework_policy_metadata_matches_registry():
    for name in NEW_15:
        framework = load_trading_framework(name); requirements = framework_policy_requirements(name)
        assert requirements["event_consumption"], name
        assert framework.metadata.state_policy_requirements, name
    assert framework_policy_requirements("pivot_range_breakout")["session"]
    assert framework_policy_requirements("pin_bar_rejection")["level"]


if __name__ == "__main__":
    test_new_framework_policy_metadata_matches_registry(); print("test_framework_expansion_35_policy passed")
