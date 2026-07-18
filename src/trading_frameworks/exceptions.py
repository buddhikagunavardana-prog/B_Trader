class TradingFrameworkError(Exception):
    """Base error for trading-framework operations."""


class FrameworkNotFoundError(TradingFrameworkError):
    """Raised when a framework name or alias is not registered."""


class FrameworkConfigurationError(TradingFrameworkError, ValueError):
    """Raised when framework parameters are invalid."""


class FrameworkDataError(TradingFrameworkError, ValueError):
    """Raised when an execution context violates the data contract."""
