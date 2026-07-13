import json
import time
from pathlib import Path

from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.mock_provider import MockProvider
from src.ai.research.research_context_builder import build_research_context
from src.ai.research.research_prompt_builder import build_research_prompt
from src.ai.research.research_schema import validate_research_analysis
from src.research.pipeline.pipeline_loader import load_json_config
from src.research.pipeline.pipeline_reporter import save_json_report


CONFIG_PATH = Path("src/config/ai_research.json")
REQUIRED_CONFIG_FIELDS = [
    "enabled", "provider", "model", "advisory_only",
    "allow_trade_execution", "allow_threshold_changes",
    "allow_configuration_changes", "max_candidates", "max_recommendations",
    "timeout_seconds", "retry_count", "output_path", "input_report_paths",
]


def load_ai_research_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_FIELDS)


def _validate_safety_config(config: dict) -> None:
    if not config.get("advisory_only", False):
        raise ValueError("AI research must remain advisory_only")
    forbidden = [
        "allow_trade_execution",
        "allow_threshold_changes",
        "allow_configuration_changes",
    ]
    if any(config.get(field, False) for field in forbidden):
        raise ValueError("AI research configuration grants forbidden authority")
    if str(config.get("provider", "")).lower() not in {"mock", "gemini"}:
        raise ValueError("AI research provider must be mock or gemini")
    if not str(config.get("model", "")):
        raise ValueError("AI research model must be configured")
    if int(config.get("max_candidates", 0)) < 1:
        raise ValueError("max_candidates must be positive")
    if int(config.get("max_recommendations", 0)) < 1:
        raise ValueError("max_recommendations must be positive")
    if float(config.get("timeout_seconds", 0)) <= 0:
        raise ValueError("timeout_seconds must be positive")
    if int(config.get("retry_count", -1)) < 0:
        raise ValueError("retry_count cannot be negative")
    if not isinstance(config.get("input_report_paths"), dict):
        raise ValueError("input_report_paths must be an object")


def _build_provider(config: dict):
    provider = str(config["provider"]).lower()
    if provider == "mock":
        return MockProvider()
    if provider == "gemini":
        return GeminiProvider(
            model=str(config["model"]),
            timeout_seconds=float(config["timeout_seconds"]),
            retry_count=int(config["retry_count"]),
        )
    raise ValueError(f"Unsupported AI provider: {provider}")


def run_research_analysis(
    config_override: dict | None = None,
    provider=None,
    write_output: bool = True,
) -> dict:
    config = load_ai_research_config()
    if config_override:
        config.update(config_override)
    _validate_safety_config(config)
    if not config["enabled"]:
        return {
            "status": "DISABLED",
            "advisory_only": True,
            "provider_called": False,
        }

    context = build_research_context(
        dict(config["input_report_paths"]),
        int(config["max_candidates"]),
    )
    prompt = build_research_prompt(context, int(config["max_recommendations"]))
    provider = provider or _build_provider(config)
    raw_response = provider.generate(prompt, context)
    try:
        payload = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("AI provider returned malformed JSON") from error
    if not isinstance(payload, dict) or not {
        "provider", "model"
    }.issubset(payload):
        raise ValueError("AI provider response is missing provider metadata")
    payload["provider"] = provider.name
    payload["model"] = provider.model
    payload = validate_research_analysis(
        payload,
        context,
        int(config["max_recommendations"]),
    )
    payload["status"] = "COMPLETED"
    payload["generated_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    payload["advisory_only"] = True
    if write_output:
        save_json_report(payload, str(config["output_path"]))
    return payload
