import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.indicators.registry import indicator_registry
from src.engines.indicator_engine import calculate_indicators
from src.strategies.json_strategy_loader import load_json_strategy_file


EXPECTED_CATEGORY_COUNTS = {
    "trend": 30,
    "momentum": 42,
    "volatility": 29,
    "volume": 25,
    "market_strength": 8,
    "structure": 15,
    "candlestick": 1,
}


def _market_data(rows: int = 120) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="15min")
    base = np.linspace(100.0, 130.0, rows)
    return pd.DataFrame(
        {
            "open": base - 0.2,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + np.sin(np.arange(rows) / 5.0),
            "volume": np.linspace(1000.0, 2500.0, rows),
        },
        index=index,
    )


def _assert_aligned(value, index: pd.Index) -> None:
    if isinstance(value, pd.Series):
        assert value.index.equals(index)
        return
    if isinstance(value, pd.DataFrame):
        assert value.index.equals(index)
        return
    if isinstance(value, (tuple, list)):
        assert value
        for item in value:
            _assert_aligned(item, index)
        return
    if isinstance(value, dict):
        assert value
        for item in value.values():
            _assert_aligned(item, index)
        return
    raise AssertionError(f"unsupported indicator output: {type(value)!r}")


def _strategy(indicators: dict) -> dict:
    return {
        "strategy_id": "indicator_contract_test",
        "name": "Indicator Contract Test",
        "timeframe": "15m",
        "indicators": indicators,
        "entry_rules": {},
        "exit_rules": {},
        "risk": {},
        "enabled": True,
    }


def test_professional_registry_inventory_and_categories():
    assert len(indicator_registry.list_names()) == 150
    assert {
        category: len(indicator_registry.list_by_category(category))
        for category in indicator_registry.list_categories()
    } == EXPECTED_CATEGORY_COUNTS


def test_every_registered_indicator_returns_index_aligned_output():
    market = _market_data()
    for name in indicator_registry.list_names():
        _assert_aligned(indicator_registry.calculate(name, market), market.index)


def test_empty_and_nan_inputs_are_safe():
    empty = _market_data(0)
    for name in indicator_registry.list_names():
        _assert_aligned(indicator_registry.calculate(name, empty), empty.index)

    market = _market_data()
    market.loc[market.index[30], "close"] = np.nan
    for name in indicator_registry.list_names():
        _assert_aligned(indicator_registry.calculate(name, market), market.index)


def test_parameter_validation_and_backward_aliases():
    assert indicator_registry.get("bollinger")["name"] == "bollinger_bands"
    assert indicator_registry.get("volume")["name"] == "volume_sma"
    for name in ["ema", "kama", "ultimate_oscillator", "price_channels"]:
        try:
            indicator_registry.validate_parameters(name, {"period": 0})
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid period accepted for {name}")
    try:
        indicator_registry.validate_parameters("ema", {"unknown": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown indicator parameter accepted")


def test_json_strategy_indicator_validation():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "strategy.json"
        path.write_text(json.dumps(_strategy({
            "kama": {"enabled": True, "period": 10},
            "vortex": {"enabled": True, "period": 14},
        })), encoding="utf-8")
        loaded = load_json_strategy_file(path)
        assert set(loaded["indicators"]) == {"kama", "vortex"}

        path.write_text(json.dumps(_strategy({
            "not_real": {"enabled": True},
        })), encoding="utf-8")
        try:
            load_json_strategy_file(path)
        except ValueError as error:
            assert "Indicator not found" in str(error)
        else:
            raise AssertionError("unknown JSON indicator accepted")


def test_registry_indicators_flow_into_research_dataframe():
    strategy = SimpleNamespace(indicators={
        "kama": {"enabled": True, "period": 10},
        "vortex": {"enabled": True, "period": 14},
    })
    result = calculate_indicators(_market_data(), strategy)
    assert {"KAMA", "VORTEX_POSITIVE", "VORTEX_NEGATIVE"}.issubset(result.columns)


def test_all_nonlegacy_registry_indicators_are_pipeline_compatible():
    legacy = {
        "ema", "rsi", "macd", "atr", "bollinger_bands", "volume_sma",
        "support_resistance", "candlestick", "supertrend",
    }
    strategy = SimpleNamespace(indicators={
        name: {"enabled": True}
        for name in indicator_registry.list_names()
        if name not in legacy
    })
    market = _market_data()
    original_ohlcv = market.copy(deep=True)
    result = calculate_indicators(market.copy(), strategy)
    assert len(result) == 120
    assert len(result.columns) > len(_market_data().columns)
    pd.testing.assert_frame_equal(
        result[list(original_ohlcv.columns)], original_ohlcv, check_exact=True,
    )


def test_representative_new_indicator_formulas():
    market = _market_data()
    standard_deviation = indicator_registry.calculate(
        "standard_deviation", market, {"period": 5},
    )
    pd.testing.assert_series_equal(
        standard_deviation,
        market["close"].rolling(5).std().rename("STANDARD_DEVIATION"),
    )

    volume_roc = indicator_registry.calculate("volume_roc", market, {"period": 3})
    expected_volume_roc = (
        100 * (market["volume"] - market["volume"].shift(3))
        / market["volume"].shift(3)
    ).rename("VOLUME_ROC")
    pd.testing.assert_series_equal(volume_roc, expected_volume_roc)

    upper, middle, lower = indicator_registry.calculate(
        "price_channels", market, {"period": 5},
    )
    pd.testing.assert_series_equal(
        upper, market["high"].rolling(5).max().rename("PRICE_CHANNEL_UPPER"),
    )
    pd.testing.assert_series_equal(
        lower, market["low"].rolling(5).min().rename("PRICE_CHANNEL_LOWER"),
    )
    pd.testing.assert_series_equal(
        middle, ((upper + lower) / 2).rename("PRICE_CHANNEL_MIDDLE"),
    )

    _, direction = indicator_registry.calculate("supertrend", market)
    assert set(direction.unique()).issubset({-1, 1})


if __name__ == "__main__":
    test_professional_registry_inventory_and_categories()
    test_every_registered_indicator_returns_index_aligned_output()
    test_empty_and_nan_inputs_are_safe()
    test_parameter_validation_and_backward_aliases()
    test_json_strategy_indicator_validation()
    test_registry_indicators_flow_into_research_dataframe()
    test_all_nonlegacy_registry_indicators_are_pipeline_compatible()
    test_representative_new_indicator_formulas()
    print("test_indicator_registry passed")
