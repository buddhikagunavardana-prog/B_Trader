from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_stochastic_pullback_trend_contract():
    run_framework_contract("stochastic_pullback_trend")


if __name__ == "__main__":
    test_stochastic_pullback_trend_contract(); print("test_stochastic_pullback_framework passed")
