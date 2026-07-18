from src.research.frameworks.adapter import run_framework_decision_series
from src.tests.framework_expansion_35_test_data import NEW_15
from src.tests.framework_expansion_test_data import config, data


def test_new_framework_state_resets():
    for name in NEW_15:
        first = run_framework_decision_series(config(name), data(name))
        second = run_framework_decision_series(config(name), data(name))
        assert first.decisions.equals(second.decisions), name
        assert first.decisions["policy_reason_code"].astype(str).str.len().gt(0).all(), name


if __name__ == "__main__":
    test_new_framework_state_resets(); print("test_framework_expansion_35_state passed")
