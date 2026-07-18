from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_chandelier_exit_trend_contract():
    run_framework_contract("chandelier_exit_trend")


if __name__ == "__main__":
    test_chandelier_exit_trend_contract(); print("test_chandelier_exit_framework passed")
