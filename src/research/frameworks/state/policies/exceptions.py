class PolicyError(ValueError):
    """Raised when a research-state policy is invalid."""


class IllegalTransitionError(PolicyError):
    """Raised when a transition violates the research lifecycle."""
