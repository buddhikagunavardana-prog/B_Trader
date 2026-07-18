import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkMetadata
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.registry import TradingFrameworkRegistry, trading_framework_registry
from src.trading_frameworks.validator import validate_registry


EXPECTED = {
    "triple_screen_trading", "turtle_trading", "ichimoku_cloud_trading",
    "bollinger_mean_reversion", "donchian_breakout",
}


def test_registry_contains_exact_phase_24_1_inventory():
    assert EXPECTED.issubset(trading_framework_registry.list_names())
    assert len(trading_framework_registry.list_definitions()) == 20
    assert set(trading_framework_registry.list_categories()) == {
        "multi_timeframe", "trend_following", "mean_reversion", "breakout", "momentum", "price_action",
    }


def test_registry_metadata_and_indicator_dependencies_are_valid():
    result = validate_registry()
    assert result.valid, result.to_dict()
    assert trading_framework_registry.canonical_name("Turtle") == "turtle_trading"
    assert {"ichimoku_cloud_trading", "turtle_trading"}.issubset(
        trading_framework_registry.list_by_category("trend_following")
    )
    assert len(trading_framework_registry.list_stable()) == 20
    assert len(trading_framework_registry.list_by_market("crypto_spot")) == 20
    assert "triple_screen_trading" in trading_framework_registry.list_by_timeframe("1h")


def test_duplicate_registration_and_missing_dependency_are_rejected():
    class MissingDependencyFramework(BaseTradingFramework):
        schema = FrameworkSchema(
            FrameworkMetadata(
                "missing_dependency", "Missing Dependency", "breakout", "Test-only framework.",
                ("execution",), {"execution": "1h"}, ("not_a_real_indicator",), ("close",),
                reference_notes="Test-only invalid dependency.",
            ),
            (), {"execution": ("close",)}, "entry", "exit", "risk", "management",
        )

        def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None):
            return self.no_trade(timestamp, "test")

    registry = TradingFrameworkRegistry()
    registry.register(MissingDependencyFramework)
    result = validate_registry(registry)
    assert not result.valid
    assert any(issue.code == "unresolved_indicator" for issue in result.issues)
    try:
        registry.register(MissingDependencyFramework)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate framework registration accepted")


if __name__ == "__main__":
    test_registry_contains_exact_phase_24_1_inventory()
    test_registry_metadata_and_indicator_dependencies_are_valid()
    test_duplicate_registration_and_missing_dependency_are_rejected()
    print("test_trading_framework_registry passed")
