from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Mapping

from src.research.frameworks.configuration import configuration_from_dict, load_research_configuration
from src.research.frameworks.historical.campaign.models import (
    CAMPAIGN_MANIFEST_VERSION,
    HistoricalCampaignConfig,
    HistoricalCampaignPlan,
    HistoricalCampaignTask,
    HistoricalResearchRange,
    HistoricalSourceSetBinding,
    safe_campaign_directory,
)
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.planner import _code_fingerprint, plan_historical_run
from src.research.run_management.run_identity import stable_identity_hash
from src.trading_frameworks.registry import trading_framework_registry


def campaign_code_fingerprint() -> str:
    digest = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    digest.update(_code_fingerprint().encode("ascii"))
    return digest.hexdigest()


def _selected_framework_names(config: HistoricalCampaignConfig) -> tuple[str, ...]:
    requested = tuple(config.framework_configuration_names)
    if any(item in {"*", "all"} for item in requested):
        if len(requested) != 1:
            raise ValueError("wildcard framework selection cannot be combined with explicit names")
        return tuple(trading_framework_registry.list_names())
    canonical = tuple(trading_framework_registry.canonical_name(name) for name in requested)
    if len(set(canonical)) != len(canonical):
        raise ValueError("campaign framework selection contains duplicate canonical frameworks")
    return tuple(sorted(canonical))


def _framework_configurations(config: HistoricalCampaignConfig, root: str | Path) -> dict[str, object]:
    directory = Path(root)
    result = {}
    for name in _selected_framework_names(config):
        path = directory / f"{name}.json"
        configuration = replace(load_research_configuration(path), run_id=None)
        if configuration.framework != name:
            raise ValueError(f"framework configuration file does not resolve to {name}: {path}")
        result[name] = configuration
    return result


def _resolve_range(binding: HistoricalSourceSetBinding, primary_role: str, research_range: HistoricalResearchRange):
    index = binding.sources[primary_role].index()
    if len(index) < 1:
        raise ValueError(f"source set {binding.name} primary source is empty")
    if research_range.start_row is not None or research_range.end_row is not None:
        start = research_range.start_row or 0
        end = len(index) if research_range.end_row is None else research_range.end_row
        if start < 0 or end > len(index) or start >= end:
            raise ValueError(f"research range {research_range.name} is outside source-set row coverage")
        return index[start], index[end - 1]
    start = research_range.start_timestamp
    end = research_range.end_timestamp
    if start is not None and int(index.searchsorted(start, side="left")) >= len(index):
        raise ValueError(f"research range {research_range.name} starts after source-set coverage")
    if end is not None and int(index.searchsorted(end, side="right")) < 1:
        raise ValueError(f"research range {research_range.name} ends before source-set coverage")
    return start, end


def _validate_binding(configuration, binding: HistoricalSourceSetBinding) -> None:
    expected = dict(configuration.timeframe_roles)
    if dict(binding.role_timeframes) != expected:
        raise ValueError(
            f"source set {binding.name} roles/timeframes do not match framework {configuration.framework}"
        )
    primary = configuration.primary_role
    if binding.execution_timeframe != expected[primary]:
        raise ValueError(f"source set {binding.name} execution timeframe does not match primary role")
    for source in binding.sources.values():
        source.validate()


def child_plan_for_task(
    campaign_plan: HistoricalCampaignPlan,
    task: HistoricalCampaignTask,
    binding: HistoricalSourceSetBinding,
):
    configuration = configuration_from_dict(dict(task.framework_configuration))
    child_values = dict(task.child_configuration)
    child_values.update(
        framework_configuration=configuration,
        output_directory=str(safe_campaign_directory(campaign_plan.config.output_root, campaign_plan.campaign_id) / "children"),
        run_id=task.child_run_id,
    )
    child_config = HistoricalResearchRunConfig(**child_values)
    child_plan = plan_historical_run(child_config, binding.sources)
    if child_plan.run_id != task.child_run_id or child_plan.configuration_fingerprint != task.child_configuration_fingerprint:
        raise ValueError(f"campaign task {task.task_id} no longer produces its deterministic child plan")
    return child_plan


def plan_historical_campaign(
    config: HistoricalCampaignConfig,
    source_sets: Mapping[str, HistoricalSourceSetBinding],
    framework_configuration_root: str | Path = "src/config/framework_research",
) -> HistoricalCampaignPlan:
    if set(config.source_set_names) != set(source_sets):
        missing = sorted(set(config.source_set_names) - set(source_sets))
        extra = sorted(set(source_sets) - set(config.source_set_names))
        raise ValueError(f"campaign source-set bindings differ from selection; missing={missing}, extra={extra}")
    bindings = {name: source_sets[name] for name in sorted(source_sets)}
    for name, binding in bindings.items():
        if binding.name != name:
            raise ValueError(f"source-set mapping key {name} does not match binding name {binding.name}")
    configurations = _framework_configurations(config, framework_configuration_root)
    configuration_fingerprints = {
        name: stable_identity_hash(configuration.to_dict(include_run_id=False))
        for name, configuration in configurations.items()
    }
    source_set_fingerprints = {name: binding.fingerprint for name, binding in bindings.items()}
    code_fingerprint = campaign_code_fingerprint()
    configuration_fingerprint = stable_identity_hash(config.identity_snapshot())
    campaign_identity = {
        "configuration": config.identity_snapshot(),
        "configuration_fingerprints": configuration_fingerprints,
        "source_set_fingerprints": source_set_fingerprints,
        "code_fingerprint": code_fingerprint,
        "historical_schema_version": "1.0",
        "manifest_schema_version": CAMPAIGN_MANIFEST_VERSION,
    }
    campaign_id = f"campaign_{stable_identity_hash(campaign_identity)}"
    campaign_directory = safe_campaign_directory(config.output_root, campaign_id)
    tasks = []
    for framework_name in sorted(configurations):
        configuration = configurations[framework_name]
        framework_fingerprint = configuration_fingerprints[framework_name]
        for source_set_name in sorted(bindings):
            binding = bindings[source_set_name]
            applicable = {
                trading_framework_registry.canonical_name(name)
                for name in binding.applicable_frameworks
                if name != "*"
            }
            if "*" not in binding.applicable_frameworks and framework_name not in applicable:
                continue
            _validate_binding(configuration, binding)
            descriptors = binding.descriptor_snapshot()
            source_fingerprints = {role: value["fingerprint"] for role, value in descriptors.items()}
            schema_fingerprints = {role: value["schema_fingerprint"] for role, value in descriptors.items()}
            for research_range in config.research_ranges:
                start, end = _resolve_range(binding, configuration.primary_role, research_range)
                stable_task_inputs = {
                    "framework_name": framework_name,
                    "framework_version": configuration.framework_version,
                    "framework_configuration_fingerprint": framework_fingerprint,
                    "source_set_name": source_set_name,
                    "source_set_fingerprint": source_set_fingerprints[source_set_name],
                    "source_fingerprints": source_fingerprints,
                    "research_range": research_range.to_dict(),
                    "resolved_start": None if start is None else str(start),
                    "resolved_end": None if end is None else str(end),
                    "campaign_configuration_fingerprint": configuration_fingerprint,
                    "code_fingerprint": code_fingerprint,
                    "schema_versions": {"campaign": CAMPAIGN_MANIFEST_VERSION, "historical": "1.0"},
                }
                seed = stable_identity_hash(stable_task_inputs)
                child_config = HistoricalResearchRunConfig(
                    run_name=f"campaign_task_{seed}",
                    framework_configuration=configuration,
                    execution_timeframe=configuration.timeframe_roles[configuration.primary_role],
                    start_timestamp=start,
                    end_timestamp=end,
                    chunk_size_rows=config.chunk_size_rows,
                    warmup_rows=config.warmup_rows,
                    warmup_safety_margin=config.warmup_safety_margin,
                    overlap_policy=config.overlap_policy,
                    output_directory=str(campaign_directory / "children"),
                    artifact_format=config.artifact_format,
                    compression=config.compression,
                    diagnostic_level=config.diagnostic_level,
                    snapshot_mode=config.snapshot_mode,
                    maximum_memory_bytes=config.maximum_memory_bytes,
                    maximum_output_rows_per_artifact=config.maximum_output_rows_per_artifact,
                    strict_integrity_mode=config.strict_integrity_mode,
                )
                child_plan = plan_historical_run(child_config, binding.sources)
                task_identity = {
                    **stable_task_inputs,
                    "historical_configuration_fingerprint": child_plan.configuration_fingerprint,
                    "child_run_id": child_plan.run_id,
                }
                task_id = f"campaign_task_{stable_identity_hash(task_identity)}"
                child_snapshot = child_config.identity_snapshot()
                child_snapshot.pop("framework_configuration")
                tasks.append(
                    HistoricalCampaignTask(
                        task_id=task_id,
                        framework_name=framework_name,
                        framework_version=configuration.framework_version,
                        framework_configuration=configuration.to_dict(include_run_id=False),
                        framework_configuration_fingerprint=framework_fingerprint,
                        source_set_name=source_set_name,
                        source_set_fingerprint=source_set_fingerprints[source_set_name],
                        source_fingerprints=source_fingerprints,
                        source_schema_fingerprints=schema_fingerprints,
                        research_range=research_range,
                        child_configuration=child_snapshot,
                        child_configuration_fingerprint=child_plan.configuration_fingerprint,
                        child_run_id=child_plan.run_id,
                        child_chunk_count=len(child_plan.chunks),
                        child_execution_row_count=child_plan.execution_row_count,
                        reason=f"{framework_name} x {source_set_name} x {research_range.name}",
                    )
                )
    planned_frameworks = {task.framework_name for task in tasks}
    missing_frameworks = sorted(set(configurations) - planned_frameworks)
    if missing_frameworks:
        raise ValueError(f"selected frameworks have no compatible source-set binding: {missing_frameworks}")
    tasks.sort(
        key=lambda item: (
            item.framework_name,
            item.framework_configuration_fingerprint,
            item.source_set_name,
            item.source_set_fingerprint,
            "" if item.research_range.start_timestamp is None else item.research_range.start_timestamp.isoformat(),
            -1 if item.research_range.start_row is None else item.research_range.start_row,
            item.task_id,
        )
    )
    task_ids = [task.task_id for task in tasks]
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("campaign matrix contains duplicate canonical tasks")
    plan_payload = {
        "campaign_id": campaign_id,
        "configuration_fingerprint": configuration_fingerprint,
        "code_fingerprint": code_fingerprint,
        "source_set_fingerprints": source_set_fingerprints,
        "tasks": [task.to_dict() for task in tasks],
        "plan_version": "1.0",
    }
    plan_fingerprint = stable_identity_hash(plan_payload)
    return HistoricalCampaignPlan(
        campaign_id,
        configuration_fingerprint,
        code_fingerprint,
        plan_fingerprint,
        source_set_fingerprints,
        tuple(tasks),
        config,
    )
