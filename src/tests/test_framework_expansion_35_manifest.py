from src.research.frameworks.manifest import build_reproducibility_manifest
from src.research.frameworks.preparation import prepare_timeframe_data
from src.tests.framework_expansion_35_test_data import NEW_15
from src.tests.framework_expansion_test_data import config, data
from src.trading_frameworks.loader import load_trading_framework


def test_new_framework_manifests_are_reproducible():
    for name in NEW_15:
        configuration = config(name); framework = load_trading_framework(name)
        prepared = prepare_timeframe_data(configuration, framework, data(name))
        first = build_reproducibility_manifest(configuration, framework, prepared)
        second = build_reproducibility_manifest(configuration, framework, prepared)
        assert first["deterministic_hash"] == second["deterministic_hash"], name
        assert first["deterministic"]["framework"] == name
        assert "policy_layer_version" in first["deterministic"]


if __name__ == "__main__":
    test_new_framework_manifests_are_reproducible(); print("test_framework_expansion_35_manifest passed")
