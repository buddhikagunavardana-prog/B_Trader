from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_pin_bar_rejection_contract():
    run_framework_contract("pin_bar_rejection")


if __name__ == "__main__":
    test_pin_bar_rejection_contract(); print("test_pin_bar_framework passed")
