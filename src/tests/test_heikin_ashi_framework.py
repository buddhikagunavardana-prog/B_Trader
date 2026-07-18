from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_heikin_ashi_trend_contract():
    run_framework_contract("heikin_ashi_trend")


if __name__ == "__main__":
    test_heikin_ashi_trend_contract(); print("test_heikin_ashi_framework passed")
