from src.research.frameworks.state.policies import OppositeSignalMode, PolicyConfiguration, PolicyDecision, PolicyReasonCode


def test_typed_models_serialize():
    config = PolicyConfiguration.from_mapping({"opposite_signal_mode": "reject"})
    assert config.opposite_signal_mode is OppositeSignalMode.REJECT
    assert PolicyDecision(False, PolicyReasonCode.COOLDOWN_ACTIVE, "blocked").to_dict()["reason_code"] == "COOLDOWN_ACTIVE"


if __name__ == "__main__":
    test_typed_models_serialize(); print("test_framework_policy_models passed")
