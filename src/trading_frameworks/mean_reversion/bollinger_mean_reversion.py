from __future__ import annotations

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


class BollingerMeanReversionFramework(BaseTradingFramework):
    minimum_history = {"execution": 1}
    schema = FrameworkSchema(
        FrameworkMetadata("bollinger_mean_reversion", "Bollinger Mean Reversion", "mean_reversion", "Band-extreme reversion framework gated by momentum and trend strength.", ("execution",), {"execution": "15m"}, ("bollinger_bands", "rsi", "zscore", "adx", "atr"), ("close", "BOLLINGER_UPPER", "BOLLINGER_MIDDLE", "BOLLINGER_LOWER", "RSI", "ZSCORE", "ADX", "ATR"), FrameworkStability.STABLE, ("bollinger_reversion", "bb_mean_reversion"), optional_indicators=("candlestick",), compatible_market_regimes=("range", "low_trend_strength"), incompatible_market_regimes=("strong_trend", "volatility_breakout"), tags=("bollinger", "mean_reversion", "range"), reference_notes="Range-gated band reversion; not a profitability claim."),
        (
            ParameterDefinition("rsi_oversold", ParameterType.FLOAT, 30.0, "Maximum RSI for a long reversion entry.", 0, 100),
            ParameterDefinition("rsi_overbought", ParameterType.FLOAT, 70.0, "Minimum RSI for a short reversion entry.", 0, 100),
            ParameterDefinition("zscore_threshold", ParameterType.FLOAT, 1.5, "Absolute Z-score required at a band extreme.", 0.1, 10),
            ParameterDefinition("maximum_adx", ParameterType.FLOAT, 25.0, "Maximum ADX allowed for range-trading entries.", 0, 100),
            ParameterDefinition("atr_stop_multiple", ParameterType.FLOAT, 1.5, "ATR stop distance.", 0.1, 20),
            ParameterDefinition("reward_multiple", ParameterType.FLOAT, 1.5, "Reward-to-stop multiple.", 0.1, 20),
            ParameterDefinition("risk_fraction", ParameterType.PERCENTAGE, 0.005, "Proposed risk fraction.", 0.0001, 0.1),
            ParameterDefinition("maximum_holding_period", ParameterType.PERIOD, 20, "Maximum-bar holding-period hint for downstream execution."),
        ),
        {"execution": ("close", "BOLLINGER_UPPER", "BOLLINGER_MIDDLE", "BOLLINGER_LOWER", "RSI", "ZSCORE", "ADX", "ATR")},
        "Enter at a completed outer-band extreme when RSI and Z-score agree and ADX indicates a range.",
        "Exit an existing position at the completed middle-band reversion target.",
        "ATR-based protective stop with deliberately smaller default risk fraction.",
        "Position state is supplied by the caller; this framework emits no orders.",
    )

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        row = context.frames["execution"].iloc[-1]
        keys = ("close", "BOLLINGER_UPPER", "BOLLINGER_MIDDLE", "BOLLINGER_LOWER", "RSI", "ZSCORE", "ADX")
        if not all(finite_number(row[key]) for key in keys):
            return self.no_trade(timestamp, "Bollinger or filter values are not warmed up.")
        price = float(row["close"]); middle = float(row["BOLLINGER_MIDDLE"])
        if context.current_position is FrameworkDirection.LONG and price >= middle:
            return self._result(timestamp, FrameworkSignal.EXIT_LONG, FrameworkDirection.FLAT, "Long reverted to the middle band.", row, -1)
        if context.current_position is FrameworkDirection.SHORT and price <= middle:
            return self._result(timestamp, FrameworkSignal.EXIT_SHORT, FrameworkDirection.FLAT, "Short reverted to the middle band.", row, 1)
        ranging = row["ADX"] <= self.parameters["maximum_adx"]
        if ranging and price <= row["BOLLINGER_LOWER"] and row["RSI"] <= self.parameters["rsi_oversold"] and row["ZSCORE"] <= -self.parameters["zscore_threshold"]:
            return self._result(timestamp, FrameworkSignal.BUY, FrameworkDirection.LONG, "Oversold lower-band extreme confirmed in a range.", row, 1)
        if ranging and price >= row["BOLLINGER_UPPER"] and row["RSI"] >= self.parameters["rsi_overbought"] and row["ZSCORE"] >= self.parameters["zscore_threshold"]:
            return self._result(timestamp, FrameworkSignal.SELL, FrameworkDirection.SHORT, "Overbought upper-band extreme confirmed in a range.", row, -1)
        return self.no_trade(timestamp, "No range-qualified band extreme is present.")

    def _result(self, timestamp, signal, direction, reason, row, side):
        risk = atr_risk(float(row["close"]), row["ATR"], side, self.parameters["atr_stop_multiple"], self.parameters["reward_multiple"], self.parameters["risk_fraction"], maximum_holding_period=self.parameters["maximum_holding_period"])
        return FrameworkDecision(self.metadata.name, timestamp, signal, direction, 0.8, reason, risk, {"price": float(row["close"]), "zscore": float(row["ZSCORE"])})
