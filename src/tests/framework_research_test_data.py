from __future__ import annotations

from src.research.frameworks.models import FrameworkResearchConfiguration, PreparationMode
from src.trading_frameworks.registry import trading_framework_registry
from src.tests.trading_framework_test_data import context_for, framework_frame


def research_configuration(name: str, mode=PreparationMode.PRECOMPUTED_ONLY, **overrides):
    framework_class = trading_framework_registry.resolve(name)
    metadata = framework_class.schema.metadata
    values = {
        "framework": name, "framework_version": metadata.version, "parameters": {},
        "symbol": "SYNTHETIC-USD", "market_type": "crypto_spot",
        "timeframe_roles": metadata.default_timeframes, "primary_role": framework_class.execution_role,
        "preparation_mode": mode,
    }
    values.update(overrides)
    return FrameworkResearchConfiguration(**values)


def precomputed_data(name: str, rows: int = 80):
    return context_for(name, rows).frames


def raw_data(name: str, rows: int = 120):
    roles = trading_framework_registry.resolve(name).schema.metadata.timeframe_roles
    return {role: framework_frame(rows, "5min")[["open", "high", "low", "close", "volume"]] for role in roles}


def synthetic_scenarios(rows: int = 80):
    up = framework_frame(rows); down = up.copy(); sideways = up.copy()
    down.loc[:, "close"] = down["close"].iloc[::-1].to_numpy()
    sideways.loc[:, "close"] = 100.0
    breakout = up.copy(); breakout.loc[breakout.index[-1], "close"] += 10.0
    false_break = breakout.copy(); false_break.loc[false_break.index[-1], "volume"] = 1.0
    bullish_pullback = up.copy(); bullish_pullback.loc[bullish_pullback.index[-2], "close"] -= 2.0
    bearish_rally = down.copy(); bearish_rally.loc[bearish_rally.index[-2], "close"] += 2.0
    sparse = up.iloc[::3].copy(); gap = up.drop(up.index[20:24]); short = up.iloc[:1].copy()
    return {
        "strong_uptrend": up, "strong_downtrend": down, "sideways_range": sideways,
        "volatility_breakout": breakout, "false_breakout": false_break,
        "bullish_pullback": bullish_pullback, "bearish_rally": bearish_rally,
        "sparse_higher_timeframe": sparse, "missing_bar_gap": gap, "short_warmup": short,
    }
