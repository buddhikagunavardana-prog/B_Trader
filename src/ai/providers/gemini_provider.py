import os
import time

from src.ai.providers.base_provider import AIProviderError, BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        timeout_seconds: float,
        retry_count: int,
    ):
        self._model = model
        self.timeout_seconds = float(timeout_seconds)
        self.retry_count = int(retry_count)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, context: dict) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AIProviderError("Gemini is enabled but GEMINI_API_KEY is missing")

        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise AIProviderError("google-genai SDK is not installed") from error

        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(
                        timeout=int(self.timeout_seconds * 1000)
                    ),
                )
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )
                text = getattr(response, "text", None)
                if not text:
                    raise AIProviderError("Gemini returned an empty or malformed response")
                return text
            except AIProviderError:
                raise
            except Exception as error:
                last_error = error
                if attempt < self.retry_count:
                    time.sleep(min(2 ** attempt, 4))

        message = str(last_error).lower()
        if "quota" in message or "resource_exhausted" in message:
            category = "quota"
        elif "model" in message or "not found" in message:
            category = "model"
        elif "timeout" in message or "deadline" in message:
            category = "timeout"
        else:
            category = "request"
        raise AIProviderError(f"Gemini {category} error after configured retries")
