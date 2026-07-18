from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_aroon_trend_contract():
    run_framework_contract("aroon_trend")


if __name__ == "__main__":
    test_aroon_trend_contract(); print("test_aroon_framework passed")
