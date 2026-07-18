import ast
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.indicators.registry import indicator_registry
from src.strategies.json_strategy_loader import load_json_strategy_file
from src.strategies.strategy_loader import load_strategy


INDICATOR_ROOT = Path("src/indicators")
STRATEGY_DEFINITIONS = Path("src/strategies/definitions")


def _market(rows: int = 180, scale: float = 1.0) -> pd.DataFrame:
    index = pd.date_range("2026-05-01", periods=rows, freq="15min")
    values = np.arange(rows, dtype=float)
    close = scale * (100.0 + 0.08 * values + 2.0 * np.sin(values / 7.0))
    return pd.DataFrame({
        "open": close - scale * 0.25 * np.cos(values / 3.0),
        "high": close + scale * (1.0 + 0.1 * np.sin(values)),
        "low": close - scale * (1.0 + 0.1 * np.cos(values)),
        "close": close,
        "volume": scale * (1_000.0 + 4.0 * values + 100.0 * np.sin(values / 5.0)),
    }, index=index)


def _outputs(value) -> list[pd.Series]:
    if isinstance(value, pd.Series):
        return [value]
    if isinstance(value, pd.DataFrame):
        return [value[column] for column in value.columns]
    if isinstance(value, (tuple, list)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    raise AssertionError(f"unsupported output: {type(value)!r}")


def _variants() -> dict[str, pd.DataFrame]:
    normal = _market()
    constant = normal.copy()
    constant[["open", "high", "low", "close"]] = 100.0
    up = normal.copy()
    up_close = np.linspace(50.0, 150.0, len(up))
    up[["open", "close"]] = np.column_stack([up_close - 0.1, up_close])
    up["high"], up["low"] = up_close + 1.0, up_close - 1.0
    down = up.iloc[::-1].copy()
    down.index = normal.index
    gaps = normal.copy()
    gaps.loc[gaps.index[::17], ["open", "high", "low", "close"]] *= 1.2
    zero_volume = normal.copy()
    zero_volume["volume"] = 0.0
    sparse = normal.copy()
    sparse.loc[sparse.index[::23], ["close", "volume"]] = np.nan
    return {
        "normal": normal,
        "constant": constant,
        "uptrend": up,
        "downtrend": down,
        "gaps": gaps,
        "zero_volume": zero_volume,
        "sparse_nan": sparse,
        "empty": normal.iloc[:0].copy(),
        "short": normal.iloc[:3].copy(),
        "large": _market(90, 1e8),
        "small": _market(90, 1e-8),
    }


def test_all_150_contracts_across_market_variants() -> None:
    names = indicator_registry.list_names()
    assert len(names) == len(set(names)) == 150
    for variant_name, market in _variants().items():
        original = market.copy(deep=True)
        for name in names:
            definition = indicator_registry.get(name)
            result = indicator_registry.calculate(name, market)
            outputs = _outputs(result)
            assert [item.name for item in outputs] == definition["output_columns"], (variant_name, name)
            for item in outputs:
                assert len(item) == len(market), (variant_name, name)
                assert item.index.equals(market.index), (variant_name, name)
                if pd.api.types.is_numeric_dtype(item.dtype):
                    assert not np.isinf(item.to_numpy()).any(), (variant_name, name)
        pd.testing.assert_frame_equal(market, original, check_exact=True)


def test_duplicate_and_unsorted_indexes_preserve_positional_contract() -> None:
    market = _market(90)
    duplicate = market.copy()
    duplicate.index = pd.Index([index // 2 for index in range(len(duplicate))])
    unsorted = market.iloc[np.r_[45:90, 0:45]].copy()
    for candidate in [duplicate, unsorted]:
        for name in indicator_registry.list_names():
            for output in _outputs(indicator_registry.calculate(name, candidate)):
                assert output.index.equals(candidate.index), name


def test_all_missing_columns_and_invalid_period_parameters_are_rejected() -> None:
    market = _market()
    for name in indicator_registry.list_names():
        definition = indicator_registry.get(name)
        missing = definition["required_columns"][0]
        try:
            indicator_registry.calculate(name, market.drop(columns=missing))
        except ValueError as error:
            assert "missing columns" in str(error)
        else:
            raise AssertionError(f"missing required column accepted: {name}")
        period_key = next(
            (
                key for key in definition["default_parameters"]
                if key == "period" or key.endswith("_period")
            ),
            None,
        )
        if period_key is None:
            continue
        try:
            indicator_registry.calculate(name, market, {period_key: 0})
        except ValueError as error:
            assert period_key in str(error)
        else:
            raise AssertionError(f"invalid parameter accepted: {name}.{period_key}")


def test_all_150_outputs_are_causal_under_future_changes() -> None:
    market = _market(220)
    changed = market.copy()
    cutoff = 145
    changed.iloc[cutoff + 1 :, :] *= 7.0
    changed.iloc[cutoff + 1 :, changed.columns.get_loc("volume")] += 1_000_000.0
    for name in indicator_registry.list_names():
        before = _outputs(indicator_registry.calculate(name, market))
        after = _outputs(indicator_registry.calculate(name, changed))
        for left, right in zip(before, after):
            pd.testing.assert_series_equal(
                left.iloc[: cutoff + 1], right.iloc[: cutoff + 1],
                check_exact=False, rtol=1e-12, atol=1e-12, obj=name,
            )


def test_static_source_has_no_known_lookahead_constructs() -> None:
    violations = []
    for path in INDICATOR_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            attribute = function.attr if isinstance(function, ast.Attribute) else ""
            if attribute == "shift" and node.args:
                value = node.args[0]
                if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
                    violations.append((path, node.lineno, "negative shift"))
            if attribute == "rolling":
                for keyword in node.keywords:
                    if keyword.arg == "center" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        violations.append((path, node.lineno, "centered rolling"))
            if attribute in {"bfill", "backfill"}:
                violations.append((path, node.lineno, "backward fill"))
    assert not violations, violations


def test_representative_formula_fixtures() -> None:
    market = _market(100)
    period = 5
    close = market["close"]
    pd.testing.assert_series_equal(
        indicator_registry.calculate("sma", market, {"period": period}),
        close.rolling(period).mean().rename("SMA"),
    )
    pd.testing.assert_series_equal(
        indicator_registry.calculate("ema", market, {"period": period}),
        close.ewm(span=period, adjust=False).mean().rename("EMA"),
    )
    weights = np.arange(1, period + 1)
    expected_wma = close.rolling(period).apply(lambda values: np.dot(values, weights) / weights.sum(), raw=True)
    pd.testing.assert_series_equal(
        indicator_registry.calculate("wma", market, {"period": period}),
        expected_wma.rename("WMA"),
    )
    ema1 = close.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    pd.testing.assert_series_equal(indicator_registry.calculate("dema", market, {"period": period}), (2 * ema1 - ema2).rename("DEMA"))
    pd.testing.assert_series_equal(indicator_registry.calculate("tema", market, {"period": period}), (3 * ema1 - 3 * ema2 + ema3).rename("TEMA"))

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    expected_rsi = (100 - 100 / (1 + gain / loss)).rename("RSI")
    pd.testing.assert_series_equal(indicator_registry.calculate("rsi", market, {"period": period}), expected_rsi)
    fast = close.ewm(span=3, adjust=False).mean()
    slow = close.ewm(span=6, adjust=False).mean()
    macd = (fast - slow).rename("MACD")
    signal = macd.ewm(span=2, adjust=False).mean().rename("MACD_SIGNAL")
    actual_macd, actual_signal, actual_histogram = indicator_registry.calculate("macd", market, {"fast": 3, "slow": 6, "signal": 2})
    pd.testing.assert_series_equal(actual_macd, macd)
    pd.testing.assert_series_equal(actual_signal, signal)
    pd.testing.assert_series_equal(actual_histogram, (macd - signal).rename("MACD_HISTOGRAM"))
    lowest, highest = market["low"].rolling(period).min(), market["high"].rolling(period).max()
    expected_k = (100 * (close - lowest) / (highest - lowest)).rename("STOCHASTIC_K")
    actual_k, actual_d = indicator_registry.calculate("stochastic", market, {"k_period": period, "d_period": 3})
    pd.testing.assert_series_equal(actual_k, expected_k)
    pd.testing.assert_series_equal(actual_d, expected_k.rolling(3).mean().rename("STOCHASTIC_D"))

    prior = close.shift()
    true_range = pd.concat([market["high"] - market["low"], (market["high"] - prior).abs(), (market["low"] - prior).abs()], axis=1).max(axis=1)
    pd.testing.assert_series_equal(indicator_registry.calculate("true_range", market), true_range.rename("TRUE_RANGE"))
    pd.testing.assert_series_equal(indicator_registry.calculate("atr", market, {"period": period}), true_range.rolling(period).mean().rename("ATR"))
    expected_std = close.rolling(period).std()
    upper, middle, lower = indicator_registry.calculate("bollinger_bands", market, {"period": period, "std_dev": 2.0})
    pd.testing.assert_series_equal(middle, close.rolling(period).mean().rename("BOLLINGER_MIDDLE"))
    pd.testing.assert_series_equal(upper, (middle + 2 * expected_std).rename("BOLLINGER_UPPER"))
    pd.testing.assert_series_equal(lower, (middle - 2 * expected_std).rename("BOLLINGER_LOWER"))

    direction = np.sign(close.diff()).fillna(0.0)
    pd.testing.assert_series_equal(indicator_registry.calculate("obv", market), (direction * market["volume"]).cumsum().rename("OBV"))
    typical = (market["high"] + market["low"] + close) / 3.0
    pd.testing.assert_series_equal(indicator_registry.calculate("vwap", market), ((typical * market["volume"]).cumsum() / market["volume"].cumsum()).rename("VWAP"))
    pivot, r1, _, _, s1, _, _ = indicator_registry.calculate("pivot_points", market)
    expected_pivot = (market["high"] + market["low"] + close) / 3.0
    pd.testing.assert_series_equal(pivot, expected_pivot.rename("PIVOT"))
    pd.testing.assert_series_equal(r1, (2 * expected_pivot - market["low"]).rename("PIVOT_R1"))
    pd.testing.assert_series_equal(s1, (2 * expected_pivot - market["high"]).rename("PIVOT_S1"))


def test_output_names_collisions_aliases_and_engine_mapping() -> None:
    owners: dict[str, list[str]] = {}
    for name in indicator_registry.list_names():
        for column in indicator_registry.get(name)["output_columns"]:
            owners.setdefault(column, []).append(name)
    assert not {column: names for column, names in owners.items() if len(names) > 1}
    assert indicator_registry.get("lsma")["name"] == "linear_regression_trend"
    assert indicator_registry.get("z_score")["name"] == "zscore"
    assert indicator_registry.get("elder_ray")["name"] == "elder_ray_index"
    nonlegacy = {
        name: {"enabled": True}
        for name in indicator_registry.list_names()
        if name not in {
            "ema", "rsi", "macd", "atr", "bollinger_bands", "volume_sma",
            "support_resistance", "candlestick", "supertrend",
        }
    }
    result = calculate_indicators(_market().copy(), SimpleNamespace(indicators=nonlegacy))
    expected = {
        column
        for name in nonlegacy
        for column in indicator_registry.get(name)["output_columns"]
    }
    assert expected.issubset(result.columns)
    assert len(result.columns) == len(set(result.columns))
    alias_result = calculate_indicators(
        _market().copy(),
        SimpleNamespace(indicators={"ppo_histogram": {"enabled": True}}),
    )
    assert {"PPO", "PPO_SIGNAL", "PPO_HISTOGRAM"}.issubset(alias_result.columns)
    try:
        calculate_indicators(
            _market().copy(),
            SimpleNamespace(indicators={
                "linear_regression_trend": {"enabled": True},
                "lsma": {"enabled": True},
            }),
        )
    except ValueError as error:
        assert "duplicate canonical indicator configuration" in str(error)
    else:
        raise AssertionError("canonical indicator plus alias silently overwrote output")


def test_strategy_definitions_and_synthetic_signal_integration() -> None:
    definitions = sorted(STRATEGY_DEFINITIONS.glob("*.json"))
    assert definitions
    configs = [load_json_strategy_file(path) for path in definitions]
    assert len({config["strategy_id"] for config in configs}) == len(configs)
    strategy = load_strategy("src/config/strategy.json")
    market = _market(260)
    prepared = calculate_indicators(market.copy(), strategy)
    signaled = generate_signals(prepared, strategy)
    assert len(signaled) == len(market)
    assert "SIGNAL" in signaled.columns
    assert set(signaled["SIGNAL"].unique()).issubset({"BUY", "SELL", "HOLD"})


if __name__ == "__main__":
    test_all_150_contracts_across_market_variants()
    test_duplicate_and_unsorted_indexes_preserve_positional_contract()
    test_all_missing_columns_and_invalid_period_parameters_are_rejected()
    test_all_150_outputs_are_causal_under_future_changes()
    test_static_source_has_no_known_lookahead_constructs()
    test_representative_formula_fixtures()
    test_output_names_collisions_aliases_and_engine_mapping()
    test_strategy_definitions_and_synthetic_signal_integration()
    print("test_indicator_library_validation passed")
