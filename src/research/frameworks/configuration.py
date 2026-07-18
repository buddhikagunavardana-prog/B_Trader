from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.research.frameworks.exceptions import ResearchConfigurationError
from src.research.frameworks.models import FrameworkResearchConfiguration
from src.research.run_management.run_identity import validate_run_id
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkStability
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.exceptions import TradingFrameworkError


CONFIG_FIELDS = set(FrameworkResearchConfiguration.__dataclass_fields__)
SUPPORTED_CONFIGURATION_VERSIONS = {"1.0"}
VALID_WARMUP_POLICIES = {"skip", "include_marked"}


def enforce_experimental_access(framework, allow_experimental: bool) -> None:
    if framework.metadata.stability is FrameworkStability.EXPERIMENTAL and not allow_experimental:
        raise ResearchConfigurationError("experimental framework requires allow_experimental=true")
    for indicator in framework.metadata.required_indicators:
        definition = __import__("src.indicators.registry", fromlist=["indicator_registry"]).indicator_registry.get(indicator)
        if definition["stability"] == "experimental" and not allow_experimental:
            raise ResearchConfigurationError(f"experimental indicator requires opt-in: {indicator}")


def validate_research_configuration(config: FrameworkResearchConfiguration) -> FrameworkResearchConfiguration:
    canonical = trading_framework_registry.canonical_name(config.framework)
    framework = load_trading_framework(canonical, config.parameters)
    if config.framework_version != framework.metadata.version:
        raise ResearchConfigurationError(f"framework version must be {framework.metadata.version}")
    if config.configuration_version not in SUPPORTED_CONFIGURATION_VERSIONS:
        raise ResearchConfigurationError(f"unsupported configuration version: {config.configuration_version}")
    if config.market_type not in framework.metadata.supported_markets:
        raise ResearchConfigurationError(f"unsupported market type: {config.market_type}")
    if not config.symbol.strip():
        raise ResearchConfigurationError("symbol must be non-empty")
    roles = set(framework.metadata.timeframe_roles)
    if set(config.timeframe_roles) != roles:
        raise ResearchConfigurationError(f"timeframe roles must be exactly {sorted(roles)}")
    if config.primary_role not in roles:
        raise ResearchConfigurationError("primary_role must be a required timeframe role")
    if config.warmup_policy not in VALID_WARMUP_POLICIES:
        raise ResearchConfigurationError(f"invalid warmup policy: {config.warmup_policy}")
    if config.start_timestamp is not None and config.end_timestamp is not None and config.start_timestamp > config.end_timestamp:
        raise ResearchConfigurationError("start_timestamp must be <= end_timestamp")
    enforce_experimental_access(framework, config.allow_experimental)
    if config.run_id:
        validate_run_id(config.run_id)
    if canonical != config.framework:
        data = config.to_dict(); data["framework"] = canonical
        return FrameworkResearchConfiguration(**data)
    return config


def configuration_from_dict(data: dict[str, Any]) -> FrameworkResearchConfiguration:
    unknown = sorted(set(data) - CONFIG_FIELDS)
    if unknown:
        raise ResearchConfigurationError(f"unknown configuration fields: {', '.join(unknown)}")
    try:
        return validate_research_configuration(FrameworkResearchConfiguration(**data))
    except (TypeError, ValueError, TradingFrameworkError) as error:
        if isinstance(error, ResearchConfigurationError):
            raise
        raise ResearchConfigurationError(str(error)) from error


def save_research_configuration(config: FrameworkResearchConfiguration, path: str | Path) -> Path:
    validated = validate_research_configuration(config)
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_research_configuration(path: str | Path) -> FrameworkResearchConfiguration:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"framework research configuration not found: {source}")
    return configuration_from_dict(json.loads(source.read_text(encoding="utf-8")))
