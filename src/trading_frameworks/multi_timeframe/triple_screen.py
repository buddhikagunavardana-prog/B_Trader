from __future__ import annotations

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import (
    FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata,
    FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType,
)
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


class TripleScreenTradingFramework(BaseTradingFramework):
    execution_role = "entry"
    minimum_history = {"trend": 1, "setup": 1, "entry": 2}
    schema = FrameworkSchema(
        metadata=FrameworkMetadata(
            name="triple_screen_trading", display_name="Triple Screen Trading",
            category="multi_timeframe",
            description="Elder-style trend, pullback, and entry screens across explicit completed-bar timeframes.",
            timeframe_roles=("trend", "setup", "entry"),
            default_timeframes={"trend": "1h", "setup": "15m", "entry": "5m"},
            required_indicators=("ema", "macd", "rsi", "stochastic", "force_index", "atr"),
            required_data_columns=("high", "low", "close", "EMA", "MACD_HISTOGRAM", "RSI", "STOCHASTIC_K", "FORCE_INDEX", "ATR"),
            stability=FrameworkStability.STABLE,
            aliases=("triple_screen", "elder_triple_screen"),
            optional_indicators=("adx", "donchian_channel"),
            compatible_market_regimes=("trend", "trend_pullback"),
            incompatible_market_regimes=("directionless_range",),
            tags=("elder", "multi_timeframe", "pullback"),
            reference_notes="Causal interpretation inspired by Alexander Elder's Triple Screen concept.",
        ),
        parameters=(
            ParameterDefinition("trend_timeframe", ParameterType.TIMEFRAME, "1h", "External completed-bar timeframe assigned to the trend role.", optimization_allowed=False),
            ParameterDefinition("setup_timeframe", ParameterType.TIMEFRAME, "15m", "External completed-bar timeframe assigned to the setup role.", optimization_allowed=False),
            ParameterDefinition("entry_timeframe", ParameterType.TIMEFRAME, "5m", "External completed-bar timeframe assigned to the entry role.", optimization_allowed=False),
            ParameterDefinition("rsi_oversold", ParameterType.FLOAT, 40.0, "Maximum setup RSI for a long pullback.", 0, 100),
            ParameterDefinition("rsi_overbought", ParameterType.FLOAT, 60.0, "Minimum setup RSI for a short pullback.", 0, 100),
            ParameterDefinition("stochastic_oversold", ParameterType.FLOAT, 30.0, "Maximum stochastic value for long setup.", 0, 100),
            ParameterDefinition("stochastic_overbought", ParameterType.FLOAT, 70.0, "Minimum stochastic value for short setup.", 0, 100),
            ParameterDefinition("atr_stop_multiple", ParameterType.FLOAT, 2.0, "ATR distance proposed for the protective stop.", 0.1, 20),
            ParameterDefinition("reward_multiple", ParameterType.FLOAT, 2.0, "Reward distance as a multiple of stop distance.", 0.1, 20),
            ParameterDefinition("risk_fraction", ParameterType.PERCENTAGE, 0.01, "Maximum account-risk fraction proposed to a downstream risk engine.", 0.0001, 0.1),
        ),
        required_columns_by_role={
            "trend": ("close", "EMA", "MACD_HISTOGRAM"),
            "setup": ("RSI", "STOCHASTIC_K", "FORCE_INDEX"),
            "entry": ("high", "low", "close", "ATR"),
        },
        entry_logic="Trade only when trend direction, counter-trend setup, and next-screen price trigger agree.",
        exit_logic="Propose an exit when the trend screen reverses against the supplied current position.",
        risk_logic="Propose ATR-based stop and reward levels plus a capped risk fraction.",
        trade_management="Stateless decisions; downstream systems own positions and order lifecycle.",
    )

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        trend = context.frames["trend"].iloc[-1]
        setup = context.frames["setup"].iloc[-1]
        entry = context.frames["entry"]
        current, prior = entry.iloc[-1], entry.iloc[-2]
        values = [trend["close"], trend["EMA"], trend["MACD_HISTOGRAM"], setup["RSI"], setup["STOCHASTIC_K"], setup["FORCE_INDEX"], current["close"]]
        if not all(finite_number(value) for value in values):
            return self.no_trade(timestamp, "Latest completed screens contain unavailable values.")
        bull_trend = trend["close"] > trend["EMA"] and trend["MACD_HISTOGRAM"] > 0
        bear_trend = trend["close"] < trend["EMA"] and trend["MACD_HISTOGRAM"] < 0
        if context.current_position is FrameworkDirection.LONG and bear_trend:
            return self._result(timestamp, FrameworkSignal.EXIT_LONG, FrameworkDirection.FLAT, 0.85, "Trend screen reversed bearish.", current)
        if context.current_position is FrameworkDirection.SHORT and bull_trend:
            return self._result(timestamp, FrameworkSignal.EXIT_SHORT, FrameworkDirection.FLAT, 0.85, "Trend screen reversed bullish.", current)
        long_setup = setup["RSI"] <= self.parameters["rsi_oversold"] and setup["STOCHASTIC_K"] <= self.parameters["stochastic_oversold"] and setup["FORCE_INDEX"] > 0
        short_setup = setup["RSI"] >= self.parameters["rsi_overbought"] and setup["STOCHASTIC_K"] >= self.parameters["stochastic_overbought"] and setup["FORCE_INDEX"] < 0
        if bull_trend and long_setup and current["close"] > prior["high"]:
            return self._result(timestamp, FrameworkSignal.BUY, FrameworkDirection.LONG, 0.9, "All three completed screens confirm a long entry.", current)
        if bear_trend and short_setup and current["close"] < prior["low"]:
            return self._result(timestamp, FrameworkSignal.SELL, FrameworkDirection.SHORT, 0.9, "All three completed screens confirm a short entry.", current)
        return self.no_trade(timestamp, "Trend, setup, and entry screens are not aligned.")

    def _result(self, timestamp, signal, direction, confidence, reason, row):
        side = 1 if signal in {FrameworkSignal.BUY, FrameworkSignal.EXIT_SHORT} else -1
        risk = atr_risk(float(row["close"]), row["ATR"], side, self.parameters["atr_stop_multiple"], self.parameters["reward_multiple"], self.parameters["risk_fraction"])
        return FrameworkDecision(self.metadata.name, timestamp, signal, direction, confidence, reason, risk, {"price": float(row["close"])})
