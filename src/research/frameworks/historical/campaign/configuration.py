from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping

from src.research.frameworks.historical.campaign.models import (
    HistoricalCampaignConfig,
    HistoricalResearchRange,
)


CONFIGURATION_FIELDS = {item.name for item in fields(HistoricalCampaignConfig)}
RANGE_FIELDS = {item.name for item in fields(HistoricalResearchRange)}


def campaign_configuration_from_dict(data: Mapping[str, Any]) -> HistoricalCampaignConfig:
    values = dict(data)
    unknown = sorted(set(values) - CONFIGURATION_FIELDS)
    if unknown:
        raise ValueError(f"unknown campaign configuration fields: {', '.join(unknown)}")
    raw_ranges = values.get("research_ranges", ())
    if not isinstance(raw_ranges, (list, tuple)):
        raise ValueError("campaign research_ranges must be a list")
    ranges = []
    for raw in raw_ranges:
        if not isinstance(raw, Mapping):
            raise ValueError("campaign research range must be an object")
        range_unknown = sorted(set(raw) - RANGE_FIELDS)
        if range_unknown:
            raise ValueError(f"unknown campaign research range fields: {', '.join(range_unknown)}")
        ranges.append(HistoricalResearchRange(**dict(raw)))
    values["research_ranges"] = tuple(ranges)
    for name in ("framework_configuration_names", "source_set_names"):
        raw = values.get(name, ())
        if not isinstance(raw, (list, tuple)):
            raise ValueError(f"campaign {name} must be a list")
        values[name] = tuple(str(item) for item in raw)
    try:
        return HistoricalCampaignConfig(**values)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid historical campaign configuration: {error}") from error


def load_campaign_configuration(path: str | Path) -> HistoricalCampaignConfig:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"historical campaign configuration not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"historical campaign configuration is unreadable: {source}") from error
    if not isinstance(payload, Mapping):
        raise ValueError("historical campaign configuration must be a JSON object")
    return campaign_configuration_from_dict(payload)
