from src.trading_frameworks.exceptions import FrameworkConfigurationError, FrameworkNotFoundError
from src.trading_frameworks.loader import load_trading_framework


def test_loader_supports_canonical_names_aliases_and_overrides():
    turtle = load_trading_framework("turtle", {"entry_period": 55, "risk_fraction": 0.005})
    assert turtle.metadata.name == "turtle_trading"
    assert turtle.parameters["entry_period"] == 55
    assert turtle.parameters["risk_fraction"] == 0.005


def test_loader_rejects_unknown_frameworks_and_invalid_parameters():
    cases = [
        ("not_real", None, FrameworkNotFoundError),
        ("turtle", {"entry_period": 0}, FrameworkConfigurationError),
        ("turtle", {"unknown": 1}, FrameworkConfigurationError),
        ("ichimoku", {"signal_mode": "future_mode"}, FrameworkConfigurationError),
    ]
    for name, parameters, expected in cases:
        try:
            load_trading_framework(name, parameters)
        except expected:
            pass
        else:
            raise AssertionError(f"invalid load accepted: {name}, {parameters}")


if __name__ == "__main__":
    test_loader_supports_canonical_names_aliases_and_overrides()
    test_loader_rejects_unknown_frameworks_and_invalid_parameters()
    print("test_trading_framework_loader passed")
