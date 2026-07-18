from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_connors_rsi_mean_reversion_contract():
    run_framework_contract("connors_rsi_mean_reversion")


if __name__ == "__main__":
    test_connors_rsi_mean_reversion_contract(); print("test_connors_rsi_framework passed")
