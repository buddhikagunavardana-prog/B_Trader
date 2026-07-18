from src.research.frameworks.manifest import build_reproducibility_manifest
from src.research.frameworks.preparation import prepare_timeframe_data
from src.tests.framework_expansion_test_data import config, data
from src.trading_frameworks.loader import load_trading_framework


def test_manifest_has_deterministic_policy_snapshot():
    c = config("ema_ribbon_trend")
    framework = load_trading_framework(c.framework)
    prepared = prepare_timeframe_data(c, framework, data(c.framework))
    manifest = build_reproducibility_manifest(c, framework, prepared)
    deterministic = manifest["deterministic"]
    assert deterministic["policy_layer_version"] == "1.0.0" and "policy_configuration_snapshot" in deterministic
    assert "aggregate_controller_timing" in manifest["runtime"] and "aggregate_controller_timing" not in deterministic


if __name__ == "__main__":
    test_manifest_has_deterministic_policy_snapshot(); print("test_framework_policy_manifest passed")
