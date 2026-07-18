from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_nr4_nr7_volatility_breakout_contract():
    run_framework_contract("nr4_nr7_volatility_breakout")


if __name__ == "__main__":
    test_nr4_nr7_volatility_breakout_contract(); print("test_nr4_nr7_framework passed")
