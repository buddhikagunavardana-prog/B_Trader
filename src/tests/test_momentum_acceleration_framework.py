from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_momentum_acceleration_breakout_contract():
    run_framework_contract("momentum_acceleration_breakout")


if __name__ == "__main__":
    test_momentum_acceleration_breakout_contract(); print("test_momentum_acceleration_framework passed")
