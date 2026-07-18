from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.trading_frameworks.models import FrameworkMetadata, ParameterDefinition


@dataclass(frozen=True)
class FrameworkSchema:
    metadata: FrameworkMetadata
    parameters: tuple[ParameterDefinition, ...]
    required_columns_by_role: dict[str, tuple[str, ...]]
    entry_logic: str
    exit_logic: str
    risk_logic: str
    trade_management: str
    causal_contract: str = (
        "Every index timestamp is a completed-bar close time. Only rows at or before "
        "the requested decision timestamp may influence the result."
    )

    def parameter_map(self) -> dict[str, ParameterDefinition]:
        return {parameter.name: parameter for parameter in self.parameters}

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "parameters": [
                {
                    "name": item.name,
                    "type": item.parameter_type.value,
                    "default": item.default,
                    "description": item.description,
                    "minimum": item.minimum,
                    "maximum": item.maximum,
                    "allowed_values": list(item.allowed_values),
                    "required": item.required,
                    "optimization_allowed": item.optimization_allowed,
                }
                for item in self.parameters
            ],
            "required_columns_by_role": {
                role: list(columns)
                for role, columns in self.required_columns_by_role.items()
            },
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "risk_logic": self.risk_logic,
            "trade_management": self.trade_management,
            "causal_contract": self.causal_contract,
        }
