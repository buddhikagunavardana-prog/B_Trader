from src.research.frameworks.state.policies import LevelRecord, PolicyConfiguration, evaluate_level_test
from src.tests.framework_policy_test_data import T0


def test_level_retest_cooldown_and_break():
    level = LevelRecord("support:1", "support", T0, T0, 100.0, 1.0)
    config = PolicyConfiguration(level_retest_cooldown_bars=2)
    assert evaluate_level_test(level, 1, False, config).allowed
    assert evaluate_level_test(level, 2, False, config).reason_code.value == "LEVEL_RETEST_COOLDOWN"
    assert evaluate_level_test(level, 4, True, config).reason_code.value == "LEVEL_INVALIDATED"


if __name__ == "__main__":
    test_level_retest_cooldown_and_break(); print("test_support_resistance_level_policy passed")
