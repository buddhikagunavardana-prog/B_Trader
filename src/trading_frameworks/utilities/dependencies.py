from __future__ import annotations

from src.indicators.registry import indicator_registry


def resolve_indicator_dependencies(names: tuple[str, ...]) -> list[dict]:
    """Resolve framework indicator names through the canonical indicator registry."""
    return [indicator_registry.get(name) for name in names]
