from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.registry import trading_framework_registry


def load_trading_framework(
    name: str,
    parameters: Mapping[str, Any] | None = None,
) -> BaseTradingFramework:
    return trading_framework_registry.resolve(name)(parameters)


def load_framework(name: str, parameters: Mapping[str, Any] | None = None) -> BaseTradingFramework:
    """Concise public alias matching the future JSON factory contract."""
    return load_trading_framework(name, parameters)


def load_framework_metadata(name: str) -> dict[str, Any]:
    return trading_framework_registry.get(name)["metadata"]
