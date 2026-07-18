from pathlib import Path
from src.tests.framework_expansion_35_test_data import NEW_15
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.validator import validate_registry
from src.trading_frameworks.loader import load_trading_framework


def test_exact_35_registry():
    names = trading_framework_registry.list_names()
    assert len(names) == 35 and len(set(names)) == 35 and set(NEW_15).issubset(names)
    assert len(list(Path("src/config/framework_research").glob("*.json"))) == 35
    assert validate_registry().valid
    invalid = (
        ("connors_rsi_mean_reversion", {"long_entry": 60, "exit_level": 50}),
        ("aroon_trend", {"strong_threshold": 20, "weak_threshold": 30}),
        ("cci_trend_pullback", {"long_setup": -40, "long_trigger": -50}),
    )
    for name, parameters in invalid:
        try: load_trading_framework(name, parameters)
        except ValueError: pass
        else: raise AssertionError(f"invalid cross-field parameters accepted: {name}")


if __name__ == "__main__":
    test_exact_35_registry(); print("test_framework_expansion_35_registry passed")
