from __future__ import annotations

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


class IchimokuCloudTradingFramework(BaseTradingFramework):
    minimum_history = {"execution": 2}
    schema = FrameworkSchema(
        FrameworkMetadata("ichimoku_cloud_trading", "Ichimoku Cloud Trading", "trend_following", "Causal Kumo, conversion/base, and lagging-confirmation framework.", ("execution",), {"execution": "4h"}, ("ichimoku_cloud", "atr"), ("close", "ICHIMOKU_CONVERSION", "ICHIMOKU_BASE", "ICHIMOKU_SPAN_A", "ICHIMOKU_SPAN_B", "ICHIMOKU_LAGGING", "ATR"), FrameworkStability.STABLE, ("ichimoku", "ichimoku_cloud"), compatible_market_regimes=("trend", "trend_transition"), incompatible_market_regimes=("choppy_range",), tags=("ichimoku", "kumo", "trend_following"), reference_notes="Uses registry-aligned causal spans; displaced chart rendering is not reconstructed."),
        (
            ParameterDefinition("signal_mode", ParameterType.ENUM, "continuation", "Signal family: continuation, kumo_breakout, or crossover.", allowed_values=("continuation", "kumo_breakout", "crossover")),
            ParameterDefinition("require_lagging_confirmation", ParameterType.BOOLEAN, True, "Require causally aligned lagging span confirmation."),
            ParameterDefinition("confirmation_strength", ParameterType.ENUM, "standard", "Confirmation strictness metadata for later research.", allowed_values=("weak", "standard", "strong")),
            ParameterDefinition("atr_stop_multiple", ParameterType.FLOAT, 2.0, "ATR stop distance.", 0.1, 20),
            ParameterDefinition("reward_multiple", ParameterType.FLOAT, 2.5, "Reward-to-stop multiple.", 0.1, 20),
            ParameterDefinition("risk_fraction", ParameterType.PERCENTAGE, 0.01, "Proposed risk fraction.", 0.0001, 0.1),
        ),
        {"execution": ("close", "ICHIMOKU_CONVERSION", "ICHIMOKU_BASE", "ICHIMOKU_SPAN_A", "ICHIMOKU_SPAN_B", "ICHIMOKU_LAGGING", "ATR")},
        "Use the selected Kumo/crossover mode only with indicator values available on the completed row.",
        "Exit when price and conversion/base structure reverse against the current position.",
        "ATR-based stop and target proposals.",
        "No forward-shift reconstruction; inputs must use the indicator registry's availability alignment.",
    )

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        frame = context.frames["execution"]
        row, prior = frame.iloc[-1], frame.iloc[-2]
        columns = ("close", "ICHIMOKU_CONVERSION", "ICHIMOKU_BASE", "ICHIMOKU_SPAN_A", "ICHIMOKU_SPAN_B", "ICHIMOKU_LAGGING")
        if not all(finite_number(row[column]) for column in columns):
            return self.no_trade(timestamp, "Ichimoku values are not warmed up.")
        price = float(row["close"]); top = max(row["ICHIMOKU_SPAN_A"], row["ICHIMOKU_SPAN_B"]); bottom = min(row["ICHIMOKU_SPAN_A"], row["ICHIMOKU_SPAN_B"])
        bullish = price > top and row["ICHIMOKU_CONVERSION"] > row["ICHIMOKU_BASE"]
        bearish = price < bottom and row["ICHIMOKU_CONVERSION"] < row["ICHIMOKU_BASE"]
        if self.parameters["signal_mode"] == "kumo_breakout":
            bullish = prior["close"] <= max(prior["ICHIMOKU_SPAN_A"], prior["ICHIMOKU_SPAN_B"]) and price > top
            bearish = prior["close"] >= min(prior["ICHIMOKU_SPAN_A"], prior["ICHIMOKU_SPAN_B"]) and price < bottom
        elif self.parameters["signal_mode"] == "crossover":
            bullish = prior["ICHIMOKU_CONVERSION"] <= prior["ICHIMOKU_BASE"] and row["ICHIMOKU_CONVERSION"] > row["ICHIMOKU_BASE"] and price > top
            bearish = prior["ICHIMOKU_CONVERSION"] >= prior["ICHIMOKU_BASE"] and row["ICHIMOKU_CONVERSION"] < row["ICHIMOKU_BASE"] and price < bottom
        if self.parameters["require_lagging_confirmation"]:
            bullish = bullish and row["ICHIMOKU_LAGGING"] > row["ICHIMOKU_BASE"]
            bearish = bearish and row["ICHIMOKU_LAGGING"] < row["ICHIMOKU_BASE"]
        if context.current_position is FrameworkDirection.LONG and bearish:
            return self._result(timestamp, FrameworkSignal.EXIT_LONG, FrameworkDirection.FLAT, "Ichimoku structure reversed bearish.", row, -1)
        if context.current_position is FrameworkDirection.SHORT and bullish:
            return self._result(timestamp, FrameworkSignal.EXIT_SHORT, FrameworkDirection.FLAT, "Ichimoku structure reversed bullish.", row, 1)
        if bullish:
            return self._result(timestamp, FrameworkSignal.BUY, FrameworkDirection.LONG, "Bullish Ichimoku structure confirmed.", row, 1)
        if bearish:
            return self._result(timestamp, FrameworkSignal.SELL, FrameworkDirection.SHORT, "Bearish Ichimoku structure confirmed.", row, -1)
        return self.no_trade(timestamp, "Ichimoku structure is neutral or unconfirmed.")

    def _result(self, timestamp, signal, direction, reason, row, side):
        risk = atr_risk(float(row["close"]), row["ATR"], side, self.parameters["atr_stop_multiple"], self.parameters["reward_multiple"], self.parameters["risk_fraction"], True)
        return FrameworkDecision(self.metadata.name, timestamp, signal, direction, 0.8, reason, risk, {"price": float(row["close"])})
