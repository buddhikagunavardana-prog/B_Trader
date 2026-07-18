from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_volume_expansion_breakout_contract():
    run_framework_contract("volume_expansion_breakout")


if __name__ == "__main__":
    test_volume_expansion_breakout_contract(); print("test_volume_expansion_framework passed")
