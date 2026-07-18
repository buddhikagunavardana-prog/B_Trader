from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_elder_impulse_system_contract():
    run_framework_contract("elder_impulse_system")


if __name__ == "__main__":
    test_elder_impulse_system_contract(); print("test_elder_impulse_framework passed")
