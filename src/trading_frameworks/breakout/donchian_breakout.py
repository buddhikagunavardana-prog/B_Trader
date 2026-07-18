from __future__ import annotations

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


class DonchianBreakoutFramework(BaseTradingFramework):
    minimum_history = {"execution": 2}
    schema = FrameworkSchema(
        FrameworkMetadata("donchian_breakout", "Donchian Breakout", "breakout", "Prior-channel breakout framework with volume and trend-strength confirmation.", ("execution",), {"execution": "1h"}, ("donchian_channel", "volume_sma", "adx", "atr"), ("high", "low", "close", "volume", "DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER", "VOLUME_SMA", "ADX", "ATR"), FrameworkStability.STABLE, ("donchian", "channel_breakout"), compatible_market_regimes=("trend", "volatility_expansion"), incompatible_market_regimes=("quiet_range",), tags=("donchian", "breakout", "confirmation"), reference_notes="A single-entry breakout model, intentionally distinct from Turtle system rules."),
        (
            ParameterDefinition("channel_period", ParameterType.PERIOD, 20, "External Donchian channel lookback."),
            ParameterDefinition("exit_period", ParameterType.PERIOD, 10, "External opposite exit-channel lookback."),
            ParameterDefinition("trigger_mode", ParameterType.ENUM, "close_break", "Trigger using close_break, high_low_break, or confirmed_close.", allowed_values=("close_break", "high_low_break", "confirmed_close")),
            ParameterDefinition("require_volume_confirmation", ParameterType.BOOLEAN, True, "Require current volume above its completed moving average."),
            ParameterDefinition("minimum_adx", ParameterType.FLOAT, 20.0, "Minimum trend strength for entries.", 0, 100),
            ParameterDefinition("atr_stop_multiple", ParameterType.FLOAT, 2.0, "ATR stop distance.", 0.1, 20),
            ParameterDefinition("reward_multiple", ParameterType.FLOAT, 2.5, "Reward-to-stop multiple.", 0.1, 20),
            ParameterDefinition("risk_fraction", ParameterType.PERCENTAGE, 0.01, "Proposed risk fraction.", 0.0001, 0.1),
        ),
        {"execution": ("high", "low", "close", "volume", "DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER", "VOLUME_SMA", "ADX", "ATR")},
        "Compare only the completed trigger bar with the prior completed Donchian boundary.",
        "Exit an existing position on an opposite prior-channel break.",
        "ATR stop and target proposal, optionally filtered by volume and ADX.",
        "Breakout timing is explicit and never uses the current bar's channel as its own trigger.",
    )

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        frame = context.frames["execution"]
        row, prior = frame.iloc[-1], frame.iloc[-2]
        values = [row["close"], row["high"], row["low"], prior["DONCHIAN_UPPER"], prior["DONCHIAN_LOWER"], row["ADX"]]
        if not all(finite_number(value) for value in values):
            return self.no_trade(timestamp, "Donchian or filter values are not warmed up.")
        high_trigger = row["close"] if self.parameters["trigger_mode"] == "close_break" else row["high"]
        low_trigger = row["close"] if self.parameters["trigger_mode"] == "close_break" else row["low"]
        volume_ok = not self.parameters["require_volume_confirmation"] or (
            finite_number(row["volume"]) and finite_number(row["VOLUME_SMA"]) and row["volume"] > row["VOLUME_SMA"]
        )
        trend_ok = row["ADX"] >= self.parameters["minimum_adx"]
        bullish = high_trigger > prior["DONCHIAN_UPPER"]
        bearish = low_trigger < prior["DONCHIAN_LOWER"]
        if self.parameters["trigger_mode"] == "confirmed_close":
            if len(frame) < 3:
                return self.no_trade(timestamp, "Confirmed-close mode requires three completed rows.")
            older = frame.iloc[-3]
            bullish = prior["close"] > older["DONCHIAN_UPPER"] and row["close"] > prior["DONCHIAN_UPPER"]
            bearish = prior["close"] < older["DONCHIAN_LOWER"] and row["close"] < prior["DONCHIAN_LOWER"]
        exit_bearish = low_trigger < prior["DONCHIAN_EXIT_LOWER"]
        exit_bullish = high_trigger > prior["DONCHIAN_EXIT_UPPER"]
        if context.current_position is FrameworkDirection.LONG and exit_bearish:
            return self._result(timestamp, FrameworkSignal.EXIT_LONG, FrameworkDirection.FLAT, "Opposite channel break exits long.", row, -1)
        if context.current_position is FrameworkDirection.SHORT and exit_bullish:
            return self._result(timestamp, FrameworkSignal.EXIT_SHORT, FrameworkDirection.FLAT, "Opposite channel break exits short.", row, 1)
        if bullish and volume_ok and trend_ok:
            return self._result(timestamp, FrameworkSignal.BUY, FrameworkDirection.LONG, "Prior Donchian high broke with filters confirmed.", row, 1)
        if bearish and volume_ok and trend_ok:
            return self._result(timestamp, FrameworkSignal.SELL, FrameworkDirection.SHORT, "Prior Donchian low broke with filters confirmed.", row, -1)
        warnings = () if volume_ok else ("Volume confirmation failed.",)
        return self.no_trade(timestamp, "No filter-qualified prior-channel break is present.", warnings)

    def _result(self, timestamp, signal, direction, reason, row, side):
        risk = atr_risk(float(row["close"]), row["ATR"], side, self.parameters["atr_stop_multiple"], self.parameters["reward_multiple"], self.parameters["risk_fraction"], True)
        return FrameworkDecision(self.metadata.name, timestamp, signal, direction, 0.85, reason, risk, {"price": float(row["close"]), "adx": float(row["ADX"])})
