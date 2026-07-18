from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.research.frameworks.exceptions import ResearchConfigurationError
from src.research.frameworks.models import FrameworkResearchConfiguration
from src.research.run_management.run_identity import validate_run_id
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkStability
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.exceptions import TradingFrameworkError
from src.research.frameworks.state.session_state import SessionConfiguration, session_snapshot


CONFIG_FIELDS = set(FrameworkResearchConfiguration.__dataclass_fields__)
SUPPORTED_CONFIGURATION_VERSIONS = {"1.0"}
VALID_WARMUP_POLICIES = {"skip", "include_marked"}
VALID_EXPIRATION_MODES = {"bars", "timestamp", "session_end", "entry_cutoff", "framework"}
VALID_OPPOSITE_MODES = {"ignore", "reject", "request_exit", "exit_then_reverse", "allow_immediate_reverse"}
VALID_NESTED_INSIDE_BAR_POLICIES = {"keep_original_mother_bar", "replace_with_latest_mother_bar", "narrow_range", "reject_nested_setup"}
VALID_DIAGNOSTIC_LEVELS = {"none", "summary", "standard", "full"}
VALID_SNAPSHOT_MODES = {"none", "final_only", "transitions_only", "full"}


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
    if config.setup_expiration_mode not in VALID_EXPIRATION_MODES:
        raise ResearchConfigurationError(f"invalid setup_expiration_mode: {config.setup_expiration_mode}")
    if config.opposite_signal_mode not in VALID_OPPOSITE_MODES:
        raise ResearchConfigurationError(f"invalid opposite_signal_mode: {config.opposite_signal_mode}")
    if config.nested_inside_bar_policy not in VALID_NESTED_INSIDE_BAR_POLICIES:
        raise ResearchConfigurationError(f"invalid nested_inside_bar_policy: {config.nested_inside_bar_policy}")
    if str(config.state_diagnostics_level).lower() not in VALID_DIAGNOSTIC_LEVELS:
        raise ResearchConfigurationError(f"invalid state_diagnostics_level: {config.state_diagnostics_level}")
    snapshot_value = config.persist_state_snapshots
    if not isinstance(snapshot_value, bool) and str(snapshot_value).lower() not in VALID_SNAPSHOT_MODES:
        raise ResearchConfigurationError(f"invalid persist_state_snapshots mode: {snapshot_value}")
    for name in ("cooldown_bars", "setup_expiration_bars", "cooldown_after_exit_bars", "cooldown_after_setup_invalidation_bars", "cooldown_after_setup_consumption_bars", "level_retest_cooldown_bars", "level_max_age_bars", "minimum_squeeze_bars", "maximum_release_to_trigger_bars"):
        if getattr(config, name) < 0:
            raise ResearchConfigurationError(f"{name} must be non-negative")
    if config.setup_expiration_mode == "bars" and config.setup_expiration_bars < 1:
        raise ResearchConfigurationError("setup_expiration_bars must be positive in bars mode")
    if config.max_hold_enforcement and (config.max_hold_bars is None or config.max_hold_bars < 1) and not config.max_hold_duration:
        raise ResearchConfigurationError("max-hold enforcement requires max_hold_bars or max_hold_duration")
    if config.max_hold_bars is not None and config.max_hold_bars < 1:
        raise ResearchConfigurationError("max_hold_bars must be positive")
    if config.max_hold_duration:
        try:
            duration = pd.Timedelta(config.max_hold_duration)
        except (TypeError, ValueError) as error:
            raise ResearchConfigurationError("max_hold_duration must be a valid positive duration") from error
        if duration <= pd.Timedelta(0):
            raise ResearchConfigurationError("max_hold_duration must be a valid positive duration")
    try:
        session_snapshot(pd.Timestamp("2026-01-01", tz="UTC"), SessionConfiguration.from_mapping(config.session_configuration))
    except (TypeError, ValueError, KeyError, OverflowError) as error:
        raise ResearchConfigurationError(f"invalid session_configuration: {error}") from error
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
