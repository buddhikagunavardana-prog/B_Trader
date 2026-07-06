from src.indicators.registry import indicator_registry


def dummy_indicator(df, period=14):
    return df


indicator_registry.register(
    name="Dummy Indicator",
    category="test",
    function=dummy_indicator,
    default_params={"period": 14}
)

print("\n===== INDICATOR REGISTRY TEST =====")
print("All Indicators:", indicator_registry.list_names())
print("Categories:", indicator_registry.list_categories())

dummy = indicator_registry.get("Dummy Indicator")

print("Dummy Name:", dummy["name"])
print("Dummy Category:", dummy["category"])
print("Dummy Params:", dummy["default_params"])

print("\nIndicator Registry test completed.")