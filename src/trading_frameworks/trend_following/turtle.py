from __future__ import annotations

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


class TurtleTradingFramework(BaseTradingFramework):
    minimum_history = {"execution": 2}
    schema = FrameworkSchema(
        FrameworkMetadata("turtle_trading", "Turtle Trading", "trend_following", "Classic channel breakout and shorter-channel exit framework.", ("execution",), {"execution": "1d"}, ("donchian_channel", "atr"), ("high", "low", "close", "DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER", "ATR"), FrameworkStability.STABLE, ("turtle",), optional_indicators=("adx",), compatible_market_regimes=("trend", "volatility_expansion"), incompatible_market_regimes=("quiet_range",), tags=("turtle", "breakout", "trend_following"), reference_notes="Phase 24.1 interpretation of the published Turtle channel and N-risk concepts."),
        (
            ParameterDefinition("entry_period", ParameterType.PERIOD, 20, "External Donchian entry-channel lookback."),
            ParameterDefinition("exit_period", ParameterType.PERIOD, 10, "External Donchian exit-channel lookback."),
            ParameterDefinition("longer_entry_period", ParameterType.PERIOD, 55, "Optional longer System 2 channel lookback."),
            ParameterDefinition("use_longer_breakout", ParameterType.BOOLEAN, False, "Select externally prepared longer entry channels when integrated later."),
            ParameterDefinition("atr_period", ParameterType.PERIOD, 20, "External ATR/N calculation lookback."),
            ParameterDefinition("pyramiding_units", ParameterType.INTEGER, 0, "Scale-in unit hint; execution remains disabled in Phase 24.1.", 0, 4),
            ParameterDefinition("atr_stop_multiple", ParameterType.FLOAT, 2.0, "Initial stop distance in ATR units.", 0.1, 20),
            ParameterDefinition("reward_multiple", ParameterType.FLOAT, 3.0, "Indicative reward distance relative to stop.", 0.1, 20),
            ParameterDefinition("risk_fraction", ParameterType.PERCENTAGE, 0.01, "Proposed risk fraction.", 0.0001, 0.1),
        ),
        {"execution": ("high", "low", "close", "DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER", "ATR")},
        "Enter when the completed close breaks the prior completed entry channel.",
        "Exit an existing position on a break of the prior completed shorter exit channel.",
        "ATR stop proposal with fixed fractional risk; no pyramiding orders are emitted.",
        "Position and pyramiding state remain downstream responsibilities.",
    )

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        frame = context.frames["execution"]
        row, prior = frame.iloc[-1], frame.iloc[-2]
        needed = [row["close"], prior["DONCHIAN_UPPER"], prior["DONCHIAN_LOWER"], prior["DONCHIAN_EXIT_UPPER"], prior["DONCHIAN_EXIT_LOWER"]]
        if not all(finite_number(value) for value in needed):
            return self.no_trade(timestamp, "Channel values are not warmed up.")
        price = float(row["close"])
        if context.current_position is FrameworkDirection.LONG and price < prior["DONCHIAN_EXIT_LOWER"]:
            return self._decision(timestamp, FrameworkSignal.EXIT_LONG, FrameworkDirection.FLAT, "Close broke the prior Turtle exit low.", row, -1)
        if context.current_position is FrameworkDirection.SHORT and price > prior["DONCHIAN_EXIT_UPPER"]:
            return self._decision(timestamp, FrameworkSignal.EXIT_SHORT, FrameworkDirection.FLAT, "Close broke the prior Turtle exit high.", row, 1)
        if price > prior["DONCHIAN_UPPER"]:
            return self._decision(timestamp, FrameworkSignal.BUY, FrameworkDirection.LONG, "Close broke the prior Turtle entry high.", row, 1)
        if price < prior["DONCHIAN_LOWER"]:
            return self._decision(timestamp, FrameworkSignal.SELL, FrameworkDirection.SHORT, "Close broke the prior Turtle entry low.", row, -1)
        return self.no_trade(timestamp, "Price remains inside the prior Turtle channel.")

    def _decision(self, timestamp, signal, direction, reason, row, side):
        risk = atr_risk(float(row["close"]), row["ATR"], side, self.parameters["atr_stop_multiple"], self.parameters["reward_multiple"], self.parameters["risk_fraction"], True, scale_in_units=self.parameters["pyramiding_units"])
        return FrameworkDecision(self.metadata.name, timestamp, signal, direction, 0.85, reason, risk, {"price": float(row["close"])})
