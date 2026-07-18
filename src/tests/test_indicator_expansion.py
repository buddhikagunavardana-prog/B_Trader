import numpy as np
import pandas as pd

from src.indicators.registry import IndicatorRegistry, indicator_registry
from src.indicators.trend.parabolic_sar import calculate_parabolic_sar


def _market_data(rows: int = 160) -> pd.DataFrame:
    index = pd.date_range("2026-02-01", periods=rows, freq="15min")
    base = np.linspace(100.0, 130.0, rows) + np.sin(np.arange(rows) / 4.0)
    return pd.DataFrame(
        {
            "open": base - 0.2,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + 0.1 * np.cos(np.arange(rows)),
            "volume": np.linspace(1_000.0, 2_500.0, rows),
        },
        index=index,
    )


def _series_outputs(value):
    if isinstance(value, pd.Series):
        return [value]
    if isinstance(value, pd.DataFrame):
        return [value[column] for column in value.columns]
    if isinstance(value, (tuple, list)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    raise AssertionError(f"unsupported output: {type(value)!r}")


def _expect_value_error(function) -> None:
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parabolic_sar_contract_and_known_uptrend() -> None:
    market = _market_data(60)
    original = market.copy(deep=True)
    sar, direction = calculate_parabolic_sar(market)
    assert len(sar) == len(market) == len(direction)
    assert sar.index.equals(market.index) and direction.index.equals(market.index)
    assert sar.name == "PARABOLIC_SAR"
    assert direction.name == "PARABOLIC_SAR_DIRECTION"
    assert np.isfinite(sar.dropna()).all()
    assert set(direction.dropna().unique()).issubset({-1.0, 1.0})
    pd.testing.assert_frame_equal(market, original)

    rising = pd.DataFrame(
        {"high": np.arange(2.0, 22.0), "low": np.arange(1.0, 21.0)},
    )
    rising_sar, rising_direction = calculate_parabolic_sar(rising)
    assert rising_direction.eq(1.0).all()
    assert rising_sar.le(rising["low"]).all()


def test_parabolic_sar_validation_and_nan_safety() -> None:
    market = _market_data(20)
    _expect_value_error(lambda: calculate_parabolic_sar(market, acceleration=0))
    _expect_value_error(
        lambda: calculate_parabolic_sar(market, acceleration=0.2, maximum=0.1),
    )
    _expect_value_error(lambda: calculate_parabolic_sar(market.drop(columns="low")))
    market.loc[market.index[5], ["high", "low"]] = np.nan
    sar, direction = calculate_parabolic_sar(market)
    assert sar.isna().iloc[5] and direction.isna().iloc[5]
    assert not np.isinf(sar.to_numpy()).any()


def test_registry_metadata_and_duplicate_protection() -> None:
    required = {
        "name", "category", "function", "callable", "required_columns",
        "default_parameters", "output_columns", "description", "dependencies",
    }
    for name in indicator_registry.list_names():
        definition = indicator_registry.get(name)
        assert required.issubset(definition)
        assert definition["output_columns"]
        assert definition["description"]

    registry = IndicatorRegistry()
    registry.register(
        "sample",
        "test",
        lambda df: df["close"],
    )
    _expect_value_error(
        lambda: registry.register(
            "sample",
            "test",
            lambda df: df["close"],
        ),
    )


def test_registry_smoke_all_outputs_are_aligned_finite_and_nonmutating() -> None:
    market = _market_data()
    original = market.copy(deep=True)
    for name in indicator_registry.list_names():
        output = indicator_registry.calculate(name, market)
        definition = indicator_registry.get(name)
        series = _series_outputs(output)
        assert len(series) == len(definition["output_columns"])
        for item in series:
            assert len(item) == len(market)
            assert item.index.equals(market.index)
            if pd.api.types.is_numeric_dtype(item.dtype):
                assert not np.isinf(item.to_numpy()).any(), name
    pd.testing.assert_frame_equal(market, original)


def test_causal_indicators_do_not_change_when_future_rows_change() -> None:
    market = _market_data()
    cutoff = 90
    changed = market.copy()
    changed.iloc[cutoff + 1 :, changed.columns.get_indexer(["high", "low", "close"])] += 500
    for name in ["ichimoku_cloud", "swing_high_low", "parabolic_sar"]:
        original = _series_outputs(indicator_registry.calculate(name, market))
        revised = _series_outputs(indicator_registry.calculate(name, changed))
        for left, right in zip(original, revised):
            pd.testing.assert_series_equal(
                left.iloc[: cutoff + 1],
                right.iloc[: cutoff + 1],
            )


if __name__ == "__main__":
    test_parabolic_sar_contract_and_known_uptrend()
    test_parabolic_sar_validation_and_nan_safety()
    test_registry_metadata_and_duplicate_protection()
    test_registry_smoke_all_outputs_are_aligned_finite_and_nonmutating()
    test_causal_indicators_do_not_change_when_future_rows_change()
    print("test_indicator_expansion passed")
