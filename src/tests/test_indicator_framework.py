import numpy as np
import pandas as pd

from src.indicators.market_strength.dmi import calculate_dmi
from src.indicators.registry import indicator_registry
from src.indicators.volatility.bollinger import calculate_bollinger


NEW_INDICATORS = {
    "linear_regression_trend", "trix", "ppo", "force_index",
    "bollinger_band_width", "bollinger_percent_b", "chandelier_exit",
    "breakout_detection", "plus_di", "minus_di", "fair_value_gap",
    "order_block", "market_structure", "trima", "alma", "zlema",
    "mcginley_dynamic", "frama", "vidya", "moving_average_envelope",
    "linear_regression_slope", "time_series_forecast", "dpo", "apo",
    "cmo", "connors_rsi", "rmi", "fisher_transform",
    "awesome_oscillator", "balance_of_power", "coppock_curve",
    "normalized_atr", "ulcer_index", "mass_index", "volume_ema",
    "chaikin_oscillator", "negative_volume_index", "positive_volume_index",
}


def _market_data(rows: int = 260) -> pd.DataFrame:
    index = pd.date_range("2026-03-01", periods=rows, freq="15min")
    values = np.arange(rows, dtype=float)
    close = 100.0 + 0.08 * values + 2.0 * np.sin(values / 7.0)
    return pd.DataFrame(
        {
            "open": close - 0.25 * np.cos(values / 3.0),
            "high": close + 1.0 + 0.1 * np.sin(values),
            "low": close - 1.0 - 0.1 * np.cos(values),
            "close": close,
            "volume": 1_000.0 + 4.0 * values + 100.0 * np.sin(values / 5.0),
        },
        index=index,
    )


def _series_outputs(value) -> list[pd.Series]:
    if isinstance(value, pd.Series):
        return [value]
    if isinstance(value, pd.DataFrame):
        return [value[column] for column in value.columns]
    if isinstance(value, (tuple, list)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    raise AssertionError(f"unsupported indicator output: {type(value)!r}")


def _expect_value_error(function) -> None:
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_new_indicator_contracts() -> None:
    assert NEW_INDICATORS.issubset(indicator_registry.list_names())
    market = _market_data()
    original = market.copy(deep=True)
    for name in sorted(NEW_INDICATORS):
        definition = indicator_registry.get(name)
        assert callable(definition["callable"])
        assert definition["required_columns"]
        assert definition["output_columns"]
        output = indicator_registry.calculate(name, market)
        series = _series_outputs(output)
        assert [item.name for item in series] == definition["output_columns"], name
        for item in series:
            assert len(item) == len(market)
            assert item.index.equals(market.index)
            if pd.api.types.is_numeric_dtype(item.dtype):
                assert not np.isinf(item.to_numpy()).any(), name

        missing = definition["required_columns"][0]
        _expect_value_error(
            lambda name=name, missing=missing: indicator_registry.calculate(
                name, market.drop(columns=missing),
            ),
        )
        period_key = next(
            (
                key for key in definition["default_parameters"]
                if key == "period" or key.endswith("_period")
            ),
            None,
        )
        if period_key:
            assert all(item.iloc[0:1].isna().all() for item in series), name
            _expect_value_error(
                lambda name=name, key=period_key: indicator_registry.calculate(
                    name, market, {key: 0},
                ),
            )
    pd.testing.assert_frame_equal(market, original, check_exact=True)
    _expect_value_error(
        lambda: indicator_registry.calculate(
            "alma", market, {"offset": 1.1},
        ),
    )
    _expect_value_error(
        lambda: indicator_registry.calculate(
            "negative_volume_index", market, {"initial_value": 0},
        ),
    )
    _expect_value_error(
        lambda: indicator_registry.calculate(
            "positive_volume_index", market, {"initial_value": 0},
        ),
    )


def test_exact_trima_ppo_force_bollinger_and_directional_values() -> None:
    market = _market_data(80)
    trima = indicator_registry.calculate("trima", market, {"period": 3})
    expected_trima = market["close"].rolling(2).mean().rolling(2).mean().rename("TRIMA")
    pd.testing.assert_series_equal(trima, expected_trima)

    ppo, signal, histogram = indicator_registry.calculate(
        "ppo", market, {"fast_period": 3, "slow_period": 6, "signal_period": 2},
    )
    fast = market["close"].ewm(span=3, adjust=False, min_periods=3).mean()
    slow = market["close"].ewm(span=6, adjust=False, min_periods=6).mean()
    expected_ppo = (100.0 * (fast - slow) / slow).rename("PPO")
    expected_signal = expected_ppo.ewm(span=2, adjust=False, min_periods=2).mean().rename("PPO_SIGNAL")
    pd.testing.assert_series_equal(ppo, expected_ppo)
    pd.testing.assert_series_equal(signal, expected_signal)
    pd.testing.assert_series_equal(histogram, (expected_ppo - expected_signal).rename("PPO_HISTOGRAM"))

    force = indicator_registry.calculate(
        "force_index", market, {"period": 1, "smoothing_period": 1},
    )
    pd.testing.assert_series_equal(
        force,
        (market["close"].diff() * market["volume"]).rename("FORCE_INDEX"),
    )

    upper, middle, lower = calculate_bollinger(market, 5, 2.0)
    width = indicator_registry.calculate("bollinger_band_width", market, {"period": 5})
    percent_b = indicator_registry.calculate("bollinger_percent_b", market, {"period": 5})
    pd.testing.assert_series_equal(width, ((upper - lower) / middle).rename("BOLLINGER_BAND_WIDTH"))
    pd.testing.assert_series_equal(
        percent_b,
        ((market["close"] - lower) / (upper - lower)).rename("BOLLINGER_PERCENT_B"),
    )

    dmi_plus, dmi_minus = calculate_dmi(market, 5)
    pd.testing.assert_series_equal(
        indicator_registry.calculate("plus_di", market, {"period": 5}),
        dmi_plus.rename("PLUS_DI"),
    )
    pd.testing.assert_series_equal(
        indicator_registry.calculate("minus_di", market, {"period": 5}),
        dmi_minus.rename("MINUS_DI"),
    )


def test_structure_and_frama_are_causal() -> None:
    market = _market_data()
    cutoff = 170
    changed = market.copy()
    changed.iloc[cutoff + 1 :, changed.columns.get_indexer(
        ["open", "high", "low", "close", "volume"],
    )] += 10_000.0
    for name in [
        "breakout_detection", "fair_value_gap", "order_block",
        "market_structure", "frama",
    ]:
        before = _series_outputs(indicator_registry.calculate(name, market))
        after = _series_outputs(indicator_registry.calculate(name, changed))
        for left, right in zip(before, after):
            pd.testing.assert_series_equal(
                left.iloc[: cutoff + 1], right.iloc[: cutoff + 1],
            )


def test_experimental_structure_confirmation_rules() -> None:
    frame = pd.DataFrame(
        {
            "open": [10.0, 9.5, 12.0, 12.5, 8.0, 7.5],
            "high": [11.0, 10.0, 13.0, 13.0, 9.0, 8.0],
            "low": [9.0, 9.0, 12.0, 11.5, 7.0, 6.5],
            "close": [10.0, 9.2, 12.5, 12.0, 7.5, 7.0],
            "volume": [100.0] * 6,
        },
    )
    bullish, bearish, lower, upper = indicator_registry.calculate("fair_value_gap", frame)
    assert bullish.iloc[2] == 1.0 and bearish.iloc[2] == 0.0
    assert lower.iloc[2] == frame["high"].iloc[0]
    assert upper.iloc[2] == frame["low"].iloc[2]


if __name__ == "__main__":
    test_new_indicator_contracts()
    test_exact_trima_ppo_force_bollinger_and_directional_values()
    test_structure_and_frama_are_causal()
    test_experimental_structure_confirmation_rules()
    print("test_indicator_framework passed")
