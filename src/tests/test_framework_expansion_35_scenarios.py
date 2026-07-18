from src.tests.framework_expansion_35_test_data import NEW_15, directional_scenario
from src.trading_frameworks.loader import load_trading_framework


def test_bullish_and_bearish_scenarios():
    for name in NEW_15:
        framework = load_trading_framework(name)
        assert framework.execute(directional_scenario(name,"long")).signal.value == "buy", name
        assert framework.execute(directional_scenario(name,"short")).signal.value == "sell", name


if __name__ == "__main__":
    test_bullish_and_bearish_scenarios(); print("test_framework_expansion_35_scenarios passed")
