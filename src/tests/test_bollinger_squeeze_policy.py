from src.research.frameworks.state.policies import PolicyConfiguration, policy_registry
from src.research.frameworks.state.policies.framework_policies import squeeze_transition


def test_squeeze_release_window_is_configured():
    config = PolicyConfiguration(minimum_squeeze_bars=3, maximum_release_to_trigger_bars=4)
    assert config.minimum_squeeze_bars == 3 and config.maximum_release_to_trigger_bars == 4
    assert policy_registry.requirements("bollinger_squeeze_breakout")["setup"]
    assert squeeze_transition("squeeze_active", squeeze_active=False, squeeze_bars=3, minimum_squeeze_bars=3, breakout_side=None, release_age=0, maximum_release_to_trigger_bars=4)[0] == "release_detected"
    assert squeeze_transition("release_detected", squeeze_active=True, squeeze_bars=3, minimum_squeeze_bars=3, breakout_side=None, release_age=1, maximum_release_to_trigger_bars=4)[0] == "invalidated"


if __name__ == "__main__":
    test_squeeze_release_window_is_configured(); print("test_bollinger_squeeze_policy passed")
