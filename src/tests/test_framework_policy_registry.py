from src.research.frameworks.state.policies import policy_registry


def test_framework_requirements_are_explicit():
    assert policy_registry.requirements("opening_range_breakout") == {"setup": True, "session": True, "level": False, "event_consumption": True}
    assert policy_registry.requirements("support_resistance_bounce")["level"]


if __name__ == "__main__":
    test_framework_requirements_are_explicit(); print("test_framework_policy_registry passed")
