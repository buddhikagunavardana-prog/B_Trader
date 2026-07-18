from __future__ import annotations

from abc import ABC, abstractmethod
from src.research.frameworks.state.policies.models import PolicyDecision


class ResearchStatePolicy(ABC):
    """Pure policy contract: callers pass all state explicitly."""

    @abstractmethod
    def evaluate(self, **context) -> PolicyDecision:
        raise NotImplementedError
