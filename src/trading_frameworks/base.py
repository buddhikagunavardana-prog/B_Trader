from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd

from src.trading_frameworks.exceptions import FrameworkConfigurationError, FrameworkDataError
from src.trading_frameworks.models import (
    FrameworkContext,
    FrameworkDecision,
    FrameworkDirection,
    FrameworkSignal,
)
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.timeframe import (
    causal_slice,
    latest_common_timestamp,
    validate_completed_bar_frame,
)


class BaseTradingFramework(ABC):
    """Deterministic decision framework. It never sizes or places an order."""

    schema: FrameworkSchema
    execution_role = "execution"
    minimum_history: Mapping[str, int] = {}

    def __init__(self, parameters: Mapping[str, Any] | None = None) -> None:
        definitions = self.schema.parameter_map()
        supplied = dict(parameters or {})
        unknown = sorted(set(supplied) - set(definitions))
        if unknown:
            raise FrameworkConfigurationError(f"unknown parameters: {', '.join(unknown)}")
        validated: dict[str, Any] = {}
        for name, definition in definitions.items():
            value = supplied.get(name, definition.default)
            try:
                validated[name] = definition.validate(value)
            except (TypeError, ValueError) as error:
                raise FrameworkConfigurationError(str(error)) from error
        self.parameters = MappingProxyType(validated)

    @property
    def metadata(self):
        return self.schema.metadata

    def execute(
        self,
        context: FrameworkContext,
        timestamp: pd.Timestamp | str | None = None,
    ) -> FrameworkDecision:
        if not isinstance(context, FrameworkContext):
            raise FrameworkDataError("context must be a FrameworkContext")
        missing_roles = [role for role in self.metadata.timeframe_roles if role not in context.frames]
        if missing_roles:
            raise FrameworkDataError(f"missing timeframe roles: {', '.join(missing_roles)}")
        for role in self.metadata.timeframe_roles:
            frame = context.frames[role]
            validate_completed_bar_frame(frame, role)
            required = self.schema.required_columns_by_role.get(role, ())
            missing = [column for column in required if column not in frame.columns]
            if missing:
                raise FrameworkDataError(f"role '{role}' missing columns: {', '.join(missing)}")
        decision_timestamp = (
            pd.Timestamp(timestamp)
            if timestamp is not None
            else latest_common_timestamp(context.frames, self.execution_role)
        )
        causal_frames = {
            role: causal_slice(context.frames[role], decision_timestamp)
            for role in self.metadata.timeframe_roles
        }
        prepared = FrameworkContext(
            causal_frames,
            current_position=context.current_position,
            symbol=context.symbol,
        )
        short = [
            f"{role} requires {minimum} rows; received {len(causal_frames[role])}"
            for role, minimum in self.minimum_history.items()
            if len(causal_frames[role]) < minimum
        ]
        if short:
            return self.no_trade(decision_timestamp, "Insufficient history.", tuple(short))
        decision = self.generate_decision(prepared, decision_timestamp)
        return replace(
            decision,
            active_timeframe=decision.active_timeframe or self.metadata.default_timeframes.get(self.execution_role),
            framework_version=self.metadata.version,
        )

    def no_trade(
        self,
        timestamp: pd.Timestamp | None,
        reason: str,
        warnings: tuple[str, ...] = (),
    ) -> FrameworkDecision:
        return FrameworkDecision(
            framework=self.metadata.name,
            timestamp=timestamp,
            signal=FrameworkSignal.NO_TRADE,
            direction=FrameworkDirection.FLAT,
            confidence=0.0,
            reason=reason,
            warnings=warnings,
            active_timeframe=self.metadata.default_timeframes.get(self.execution_role),
            framework_version=self.metadata.version,
        )

    @abstractmethod
    def generate_decision(
        self,
        context: FrameworkContext,
        timestamp: pd.Timestamp | None,
    ) -> FrameworkDecision:
        """Generate one read-only decision from causally sliced frames."""
