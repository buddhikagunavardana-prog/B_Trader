from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd


class FrameworkSignal(str, Enum):
    BUY = "buy"
    SELL = "sell"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"
    NO_TRADE = "no_trade"


class FrameworkDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class FrameworkStability(str, Enum):
    STABLE = "stable"
    EXPERIMENTAL = "experimental"


class ParameterType(str, Enum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"
    TIMEFRAME = "timeframe"
    PERCENTAGE = "percentage"
    PERIOD = "period"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    parameter_type: ParameterType
    default: Any
    description: str
    minimum: float | None = None
    maximum: float | None = None
    allowed_values: tuple[Any, ...] = ()
    required: bool = True
    optimization_allowed: bool = True

    def validate(self, value: Any) -> Any:
        if value is None and self.parameter_type is ParameterType.OPTIONAL:
            return value
        if self.parameter_type in {ParameterType.INTEGER, ParameterType.PERIOD}:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{self.name} must be an integer")
            if self.parameter_type is ParameterType.PERIOD and value <= 0:
                raise ValueError(f"{self.name} must be positive")
        elif self.parameter_type in {ParameterType.FLOAT, ParameterType.PERCENTAGE}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{self.name} must be numeric")
            value = float(value)
            if not isfinite(value):
                raise ValueError(f"{self.name} must be finite")
        elif self.parameter_type is ParameterType.BOOLEAN and not isinstance(value, bool):
            raise TypeError(f"{self.name} must be boolean")
        elif self.parameter_type in {ParameterType.STRING, ParameterType.ENUM, ParameterType.TIMEFRAME}:
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"{self.name} must be a non-empty string")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"{self.name} must be >= {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"{self.name} must be <= {self.maximum}")
        if self.allowed_values and value not in self.allowed_values:
            raise ValueError(f"{self.name} must be one of {self.allowed_values}")
        return value


@dataclass(frozen=True)
class FrameworkMetadata:
    name: str
    display_name: str
    category: str
    description: str
    timeframe_roles: tuple[str, ...]
    default_timeframes: Mapping[str, str]
    required_indicators: tuple[str, ...]
    required_data_columns: tuple[str, ...]
    stability: FrameworkStability = FrameworkStability.STABLE
    aliases: tuple[str, ...] = ()
    version: str = "1.0.0"
    attribution: str = "B Trader reference implementation"
    supported_markets: tuple[str, ...] = ("crypto_spot", "crypto_perpetual", "forex", "equities")
    supported_directions: tuple[FrameworkDirection, ...] = (FrameworkDirection.LONG, FrameworkDirection.SHORT)
    supported_timeframes: tuple[str, ...] = ()
    optional_indicators: tuple[str, ...] = ()
    compatible_market_regimes: tuple[str, ...] = ()
    incompatible_market_regimes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    experimental_notes: str = ""
    reference_notes: str = ""
    causality_notes: str = "Completed-bar inputs only; future rows are never read."
    research_limitations: str = "Research decision proposal only; historical efficacy is not established."
    state_policy_requirements: tuple[str, ...] = ()
    execution_warning: str = "No orders, quantities, balances, fills, or profitability calculations."

    def __post_init__(self) -> None:
        if not self.supported_timeframes:
            object.__setattr__(self, "supported_timeframes", tuple(dict.fromkeys(self.default_timeframes.values())))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["stability"] = self.stability.value
        result["default_timeframes"] = dict(self.default_timeframes)
        result["supported_directions"] = [item.value for item in self.supported_directions]
        return result


@dataclass(frozen=True)
class RiskProposal:
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_fraction: float | None = None
    volatility_unit: float | None = None
    trailing_stop: bool = False
    notes: tuple[str, ...] = ()
    stop_type: str = "none"
    stop_distance: float | None = None
    take_profit_type: str = "none"
    reward_to_risk: float | None = None
    trailing_stop_type: str = "none"
    position_sizing_hint: str = "fractional_risk"
    maximum_holding_period: int | None = None
    scale_in_units: int = 0
    scale_out_fraction: float | None = None

    def __post_init__(self) -> None:
        for name in ("stop_loss", "take_profit", "risk_fraction", "volatility_unit", "stop_distance", "reward_to_risk", "scale_out_fraction"):
            value = getattr(self, name)
            if value is not None and not isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.risk_fraction is not None and not 0 < self.risk_fraction <= 1:
            raise ValueError("risk_fraction must be in (0, 1]")


@dataclass(frozen=True)
class FrameworkDecision:
    framework: str
    timestamp: pd.Timestamp | None
    signal: FrameworkSignal
    direction: FrameworkDirection
    confidence: float
    reason: str
    risk: RiskProposal = field(default_factory=RiskProposal)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    entry_allowed: bool | None = None
    exit_requested: bool | None = None
    entry_reason: str = ""
    exit_reason: str = ""
    active_timeframe: str | None = None
    framework_version: str = "1.0.0"
    position_sizing_hint: str | None = None

    def __post_init__(self) -> None:
        if not isfinite(float(self.confidence)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))
        entry_signals = {FrameworkSignal.BUY, FrameworkSignal.SELL}
        exit_signals = {FrameworkSignal.EXIT_LONG, FrameworkSignal.EXIT_SHORT}
        if self.entry_allowed is None:
            object.__setattr__(self, "entry_allowed", self.signal in entry_signals)
        if self.exit_requested is None:
            object.__setattr__(self, "exit_requested", self.signal in exit_signals)
        if not self.entry_reason and self.signal in entry_signals:
            object.__setattr__(self, "entry_reason", self.reason)
        if not self.exit_reason and self.signal in exit_signals:
            object.__setattr__(self, "exit_reason", self.reason)
        if self.position_sizing_hint is None:
            object.__setattr__(self, "position_sizing_hint", self.risk.position_sizing_hint)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "timestamp": None if self.timestamp is None else self.timestamp.isoformat(),
            "signal": self.signal.value,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "risk": asdict(self.risk),
            "diagnostics": dict(self.diagnostics),
            "warnings": list(self.warnings),
            "entry_allowed": self.entry_allowed,
            "exit_requested": self.exit_requested,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "active_timeframe": self.active_timeframe,
            "framework_version": self.framework_version,
            "position_sizing_hint": self.position_sizing_hint,
        }


@dataclass(frozen=True)
class FrameworkContext:
    frames: Mapping[str, pd.DataFrame]
    current_position: FrameworkDirection = FrameworkDirection.FLAT
    symbol: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "frames", MappingProxyType(dict(self.frames)))
