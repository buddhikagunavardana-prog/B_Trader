from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_williams_r_reversal_contract():
    run_framework_contract("williams_r_reversal")


if __name__ == "__main__":
    test_williams_r_reversal_contract(); print("test_williams_r_framework passed")
