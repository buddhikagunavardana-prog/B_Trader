from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    """Safe provider failure that never includes credentials."""


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, context: dict) -> str:
        raise NotImplementedError
