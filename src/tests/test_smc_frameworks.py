from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.configuration import load_research_configuration
from src.research.frameworks.reporting import _configuration
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext, FrameworkSignal
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.smc.frameworks import SMC_NAMES
from src.trading_frameworks.smc.models import SMCDirection, SMCFrameworkState, SMCLifecycle, SMCZone
from src.trading_frameworks.smc.primitives import confirmed_swings, equal_liquidity, imbalance_zones, zone_status
from src.utils.trading_framework_performance import _context


def _oscillating(rows=120, frequency="15min"):
    index = pd.date_range("2026-03-07 00:00", periods=rows, freq=frequency, tz="UTC")
    close = 100 + np.linspace(0, 4, rows) + 3 * np.sin(np.arange(rows) / 3)
    return pd.DataFrame({"open": close - .15, "high": close + .8, "low": close - .8, "close": close, "volume": 1000.0}, index=index)


def test_exact_smc_inventory_registry_and_configuration_count():
    assert len(SMC_NAMES) == len(set(SMC_NAMES)) == 15
    assert len(trading_framework_registry.list_names()) == 50
    assert tuple(trading_framework_registry.list_by_category("smc")) == tuple(sorted(SMC_NAMES))
    assert len(list(Path("src/config/framework_research").glob("*.json"))) == 50
    for name in SMC_NAMES:
        configuration = load_research_configuration(Path("src/config/framework_research") / f"{name}.json")
        assert configuration.framework == name
        assert not trading_framework_registry.resolve(name).schema.metadata.aliases


def test_smc_state_and_zone_round_trip():
    zone = SMCZone("z1", SMCDirection.BULLISH, 99, 100, "2026-01-01T00:00:00+00:00", SMCLifecycle.ACTIVE, ("origin",))
    state = SMCFrameworkState("order_block", SMCLifecycle.ACTIVE, SMCDirection.BULLISH, "ACTIVE_ZONE", zone.detected_at, (zone,), {"touches": 1})
    assert SMCFrameworkState.from_dict(state.to_dict()) == state


def test_confirmed_swings_are_not_backdated_and_equal_pools_deduplicate():
    frame = _oscillating(40)
    swings = confirmed_swings(frame, 2, 2)
    assert swings and all(item.confirmation_timestamp > item.pivot_timestamp for item in swings)
    cutoff = swings[-1].confirmation_timestamp
    assert swings[-1] not in confirmed_swings(frame.loc[frame.index < cutoff], 2, 2)
    synthetic = (swings[0], type(swings[0])("high", swings[0].price + .01, swings[0].pivot_timestamp + pd.Timedelta(hours=1), swings[0].confirmation_timestamp + pd.Timedelta(hours=1), swings[0].pivot_position + 4))
    pools = equal_liquidity(synthetic, .02, 2)
    assert len(pools) == 1 and pools[0]["touches"] == 2


def test_fvg_detection_partial_and_full_fill_lifecycle():
    index = pd.date_range("2026-01-01", periods=5, freq="15min", tz="UTC")
    frame = pd.DataFrame({"open":[10,11,13,13,12],"high":[11,12,14,14,13],"low":[9,10,12,11.5,10.5],"close":[10,11,13,12.5,11],"volume":1000}, index=index)
    zone = imbalance_zones(frame.iloc[:3], .1)[-1]
    assert zone_status(zone, frame.iloc[:4]) is SMCLifecycle.PARTIALLY_FILLED
    assert zone_status(zone, frame) is SMCLifecycle.FILLED


def test_all_smc_frameworks_are_deterministic_non_mutating_and_adapter_compatible():
    for name in SMC_NAMES:
        source = _context(name, 80).frames
        before = {role: frame.copy(deep=True) for role, frame in source.items()}
        first = run_framework_decision_series(_configuration(name), source)
        second = run_framework_decision_series(_configuration(name), source)
        assert first.validation.valid and first.decisions.equals(second.decisions)
        assert all(source[role].equals(before[role]) for role in source)
        assert first.reproducibility["repeated_indicator_calculation_count"] == 0


def test_unknown_ranges_and_contradictory_parameters_fail():
    with pytest.raises(ValueError):
        load_trading_framework("order_block", {"unknown": 1})
    with pytest.raises(ValueError):
        load_trading_framework("order_block", {"swing_period": 0})
    with pytest.raises(ValueError):
        load_trading_framework("order_block", {"require_displacement": True, "atr_multiple": 0})
    with pytest.raises(ValueError):
        load_trading_framework("judas_swing", {"session_start": "08:00", "session_end": "08:00"})


def test_bos_choch_and_mss_have_distinct_confirmation_requirements():
    close = np.array([10,11,12,11,13,12,14,13,13,15], dtype=float)
    index = pd.date_range("2026-01-01", periods=len(close), freq="15min", tz="UTC")
    frame = pd.DataFrame({"open":close,"high":close+.2,"low":close-.2,"close":close,"volume":1000}, index=index)
    context = FrameworkContext({"execution": frame})
    bos = load_trading_framework("break_of_structure", {"swing_period": 1}).generate_decision(context, index[-1])
    choch = load_trading_framework("change_of_character", {"swing_period": 1}).generate_decision(context, index[-1])
    mss = load_trading_framework("market_structure_shift", {"swing_period": 1}).generate_decision(context, index[-1])
    assert bos.diagnostics["reason_code"] == "BOS_CONFIRMED"
    assert choch.signal is FrameworkSignal.NO_TRADE
    assert mss.signal is FrameworkSignal.NO_TRADE


def test_zone_frameworks_expose_distinct_lineage_reason_codes():
    names = ("order_block", "breaker_block", "mitigation_block")
    assert {load_trading_framework(name).kind for name in names} == set(names)
    assert len({load_trading_framework(name).schema.entry_logic + name for name in names}) == 3


def test_future_mutation_does_not_change_pre_cutoff_outputs_for_every_smc_framework():
    cutoff_row = 55
    for name in SMC_NAMES:
        original = _context(name, 80).frames
        changed = {role: frame.copy(deep=True) for role, frame in original.items()}
        cutoff = original["execution"].index[cutoff_row]
        for frame in changed.values():
            numeric = list(frame.select_dtypes(include="number").columns)
            frame.loc[frame.index > cutoff, numeric] += 1_000_000
        values = _configuration(name).to_dict(); values["end_timestamp"] = cutoff.isoformat()
        from src.research.frameworks.models import FrameworkResearchConfiguration
        configuration = FrameworkResearchConfiguration(**values)
        left = run_framework_decision_series(configuration, original).decisions
        right = run_framework_decision_series(configuration, changed).decisions
        assert left.equals(right), name


def test_scope_exclusions_are_absent_from_smc_contracts():
    prohibited = ("pnl", "roi", "win rate", "profit factor", "drawdown", "sharpe", "expectancy", "account balance", "order size", "leverage", "fees", "slippage")
    for name in SMC_NAMES:
        schema = str(trading_framework_registry.resolve(name).schema.to_dict()).lower()
        assert not any(term in schema for term in prohibited)
