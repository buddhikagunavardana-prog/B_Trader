from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_engulfing_confirmation_trend_contract():
    run_framework_contract("engulfing_confirmation_trend")


if __name__ == "__main__":
    test_engulfing_confirmation_trend_contract(); print("test_engulfing_confirmation_framework passed")
