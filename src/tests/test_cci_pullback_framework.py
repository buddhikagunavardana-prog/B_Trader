from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_cci_trend_pullback_contract():
    run_framework_contract("cci_trend_pullback")


if __name__ == "__main__":
    test_cci_trend_pullback_contract(); print("test_cci_pullback_framework passed")
