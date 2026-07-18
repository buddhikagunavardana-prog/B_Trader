class FrameworkResearchError(Exception):
    """Base error for framework research adapter operations."""


class ResearchConfigurationError(FrameworkResearchError, ValueError):
    pass


class ResearchPreparationError(FrameworkResearchError, ValueError):
    pass


class ResearchAlignmentError(FrameworkResearchError, ValueError):
    pass
