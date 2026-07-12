from pathlib import Path

import numpy as np
import pandas as pd

from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.strategies.json_strategy_loader import (
    load_enabled_json_strategies,
    load_json_strategy_file,
)
from src.strategies.professional.compression_expansion_breakout import generate_compression_breakout_signals
from src.strategies.professional.cross_sectional_relative_strength import rank_relative_strength
from src.strategies.professional.portfolio import strategies_for_regime
from src.strategies.professional.regime_gated_mean_reversion import generate_regime_mean_reversion_signals
from src.strategies.professional.risk import (
    calculate_position_notional,
    cooldown_allows_entry,
    drawdown_risk_multiplier,
)
from src.strategies.professional.research_report import empty_professional_research_report
from src.strategies.template_registry import StrategyTemplateRegistry
from src.strategies.professional.trend_pullback_continuation import generate_trend_pullback_signals
from src.strategies.professional.volatility_scaled_time_series_momentum import generate_time_series_momentum_signals
from src.strategies.strategy_factory import create_strategy_from_json_config
from src.research.generated_candidate_experiment import _run_records


DEFINITIONS = Path("src/strategies/definitions")
PROFESSIONAL_FILES = sorted(DEFINITIONS.glob("professional_*.json"))


def _market(rows=240, slope=0.1):
    close = 100 + np.arange(rows) * slope + np.sin(np.arange(rows) / 5)
    return pd.DataFrame({
        "open": close - 0.2,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.linspace(1000, 2000, rows),
    })


def _pullback_market(rows=320):
    close = 100 + np.arange(rows) * 0.15
    close[np.arange(rows) % 20 == 18] -= 6.0
    return pd.DataFrame({
        "open": close - 0.2, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": np.linspace(1000, 2000, rows),
    })


def _load_professional():
    return [load_json_strategy_file(path) for path in PROFESSIONAL_FILES]


def test_all_professional_definitions_load_and_ids_are_unique():
    configs = _load_professional()
    assert len(configs) == 5
    assert len({config["strategy_id"] for config in configs}) == 5
    assert all(config["enabled"] is False for config in configs)
    assert all(config["metadata"]["status"] == "RESEARCH_CANDIDATE" for config in configs)
    assert all("simulated_exit_mode" in config["exit_rules"] for config in configs)
    assert len(load_enabled_json_strategies()) == 10


def test_single_pair_professional_strategies_produce_valid_signals_after_warmup():
    for config in _load_professional():
        if config["metadata"]["role"] == "overlay":
            continue
        strategy = create_strategy_from_json_config(config)
        market = _market()
        original = market.copy(deep=True)
        prepared = calculate_indicators(market.copy(), strategy)
        signaled = generate_signals(prepared, strategy)
        repeated = generate_signals(prepared, strategy)
        pd.testing.assert_frame_equal(market, original, check_exact=True)
        pd.testing.assert_series_equal(signaled["SIGNAL"], repeated["SIGNAL"], check_exact=True)
        assert set(signaled["SIGNAL"].unique()).issubset({"BUY", "HOLD"})
        assert (signaled["SIGNAL"].iloc[:20] == "HOLD").all()


def test_donchian_breakout_uses_only_previous_completed_highs():
    rows = 30
    frame = pd.DataFrame({
        "close": [10.0] * (rows - 1) + [12.0],
        "high": [10.5] * rows,
        "BB_UPPER": [11.0] * rows,
        "BB_LOWER": [9.0] * rows,
        "KELTNER_UPPER": [12.0] * rows,
        "KELTNER_LOWER": [8.0] * rows,
        "volume": [200.0] * rows,
        "VOL_SMA20": [100.0] * rows,
    })
    strategy = create_strategy_from_json_config(load_json_strategy_file(
        DEFINITIONS / "professional_compression_breakout.json",
    ))
    first = generate_compression_breakout_signals(frame, strategy)
    frame.loc[rows - 1, "high"] = 1000.0
    second = generate_compression_breakout_signals(frame, strategy)
    pd.testing.assert_series_equal(first, second)
    assert first.iloc[-1] == "BUY"


def test_breakout_requires_prior_squeeze_history():
    frame = pd.DataFrame({
        "close": [10.0] * 29 + [12.0], "high": [10.5] * 30,
        "BB_UPPER": [11.0] * 30, "BB_LOWER": [9.0] * 30,
        "KELTNER_UPPER": [10.0] * 30, "KELTNER_LOWER": [10.0] * 30,
        "volume": [200.0] * 30, "VOL_SMA20": [100.0] * 30,
    })
    strategy = create_strategy_from_json_config(load_json_strategy_file(
        DEFINITIONS / "professional_compression_breakout.json",
    ))
    assert (generate_compression_breakout_signals(frame, strategy) == "HOLD").all()


def test_pullback_uses_previous_bar_rsi_and_close():
    frame = pd.DataFrame({
        "close": [99.0, 101.0], "EMA20": [100.0, 100.0],
        "EMA48": [110.0, 111.0], "EMA192": [100.0, 101.0],
        "RSI3": [15.0, 80.0], "ADX14": [20.0, 20.0],
    })
    strategy = create_strategy_from_json_config(load_json_strategy_file(
        DEFINITIONS / "professional_trend_pullback.json",
    ))
    # Add enough historical structure values for the eight-bar slope rule.
    frame = pd.concat([pd.DataFrame({
        "close": [105.0] * 8, "EMA20": [100.0] * 8, "EMA48": [108.0] * 8,
        "EMA192": np.linspace(90, 99, 8), "RSI3": [50.0] * 8, "ADX14": [20.0] * 8,
    }), frame], ignore_index=True)
    assert generate_trend_pullback_signals(frame, strategy).iloc[-1] == "BUY"


def test_mean_reversion_is_blocked_in_trending_regime():
    frame = pd.DataFrame({
        "close": [90.0], "EMA32": [100.0], "EMA96": [100.0], "ADX14": [10.0],
        "ZSCORE": [-3.0], "BB_LOWER": [95.0], "RSI2": [5.0],
        "ROLLING_VWAP": [100.0], "REGIME": ["TRENDING"],
    })
    strategy = create_strategy_from_json_config(load_json_strategy_file(
        DEFINITIONS / "professional_regime_mean_reversion.json",
    ))
    assert generate_regime_mean_reversion_signals(frame, strategy).iloc[0] == "HOLD"


def test_cross_sectional_overlay_is_asof_safe_and_respects_limits():
    data = {
        pair: _market(260, slope)
        for pair, slope in zip(
            ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
            [0.10, 0.14, 0.08, 0.18, 0.05],
        )
    }
    before = rank_relative_strength(data, as_of=220)
    changed = {pair: frame.copy() for pair, frame in data.items()}
    changed["SOLUSDT"].loc[221:, "close"] *= 10
    after = rank_relative_strength(changed, as_of=220)
    pd.testing.assert_frame_equal(before, after, check_exact=True)
    assert len(before) <= 2
    if not before.empty:
        assert abs(before["Weight"].sum() - 1.0) < 1e-12
        assert before["Pair"].is_unique

    stale = {pair: frame.copy() for pair, frame in data.items()}
    stale["SOLUSDT"] = stale["SOLUSDT"].iloc[:-1]
    stale_result = rank_relative_strength(stale)
    assert "SOLUSDT" not in stale_result["Pair"].tolist()
    assert rank_relative_strength({"ETHUSDT": data["ETHUSDT"]}).empty
    assert rank_relative_strength({}).empty
    try:
        rank_relative_strength(data, top_count=0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid overlay top_count accepted")


def test_shared_risk_cooldown_and_regime_routing():
    notional = calculate_position_notional(10000, 0.35, 100, 98)
    assert notional == 1750.0
    assert cooldown_allows_entry(18, 10, 8)
    assert not cooldown_allows_entry(17, 10, 8)
    assert drawdown_risk_multiplier(5.9) == 1.0
    assert drawdown_risk_multiplier(6.0) == 0.5
    assert drawdown_risk_multiplier(10.0) == 0.0
    assert strategies_for_regime("SIDEWAYS") == ["PRO_REGIME_MEAN_REVERSION_V1"]
    assert "PRO_REGIME_MEAN_REVERSION_V1" not in strategies_for_regime("TRENDING")


def test_candidate_template_and_unavailable_report_contracts():
    config = StrategyTemplateRegistry().build_strategy_config({
        "template_name": "professional_momentum",
        "parameters": {
            "fast_ema": 32, "slow_ema": 96, "donchian_period": 20,
            "adx_threshold": 18, "stop_loss_pct": 2.0, "take_profit_pct": 100.0,
        },
    })
    assert config["strategy_id"].startswith("PRO_TS_MOMENTUM_V1_")
    assert config["metadata"]["status"] == "RESEARCH_CANDIDATE"
    report = empty_professional_research_report()
    assert report.empty
    assert {"Profit Factor", "Walk Forward Efficiency", "Monte Carlo Survival"}.issubset(report.columns)


def test_actual_simulated_exit_mode_is_reported():
    config = load_json_strategy_file(DEFINITIONS / "professional_trend_pullback.json")
    strategy = create_strategy_from_json_config(config)
    record = {
        "strategy_id": config["strategy_id"], "strategy_name": config["name"],
        "strategy_source": "PROFESSIONAL", "template_type": "professional_pullback",
        "strategy": strategy,
    }
    trades = []
    report, _ = _run_records([record], {"BTCUSDT": _pullback_market()}, ["BTCUSDT"], "15m", trades)
    assert report.iloc[0]["Simulated Exit Mode"] == "fixed_percent_full_position"
    assert trades
    assert all(trade["Simulated Exit Mode"] == "fixed_percent_full_position" for trade in trades)


if __name__ == "__main__":
    test_all_professional_definitions_load_and_ids_are_unique()
    test_single_pair_professional_strategies_produce_valid_signals_after_warmup()
    test_donchian_breakout_uses_only_previous_completed_highs()
    test_breakout_requires_prior_squeeze_history()
    test_pullback_uses_previous_bar_rsi_and_close()
    test_mean_reversion_is_blocked_in_trending_regime()
    test_cross_sectional_overlay_is_asof_safe_and_respects_limits()
    test_shared_risk_cooldown_and_regime_routing()
    test_candidate_template_and_unavailable_report_contracts()
    test_actual_simulated_exit_mode_is_reported()
    print("test_professional_strategies passed")
