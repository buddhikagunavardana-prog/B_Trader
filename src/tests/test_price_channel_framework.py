from src.tests.framework_expansion_35_test_data import run_framework_contract


def test_price_channel_trend_contract():
    run_framework_contract("price_channel_trend")


if __name__ == "__main__":
    test_price_channel_trend_contract(); print("test_price_channel_framework passed")
