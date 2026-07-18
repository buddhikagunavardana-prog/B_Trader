from __future__ import annotations

from src.research.frameworks.historical.campaign.models import (
    HistoricalCampaignConfig,
    HistoricalResearchRange,
    HistoricalSourceSetBinding,
)
from src.research.frameworks.historical.source import source_bundle
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context


def binding_for(name: str, framework: str, rows: int = 60) -> HistoricalSourceSetBinding:
    frames = {role: frame.copy(deep=True) for role, frame in _context(framework, rows).frames.items()}
    sources = source_bundle(frames)
    from src.research.frameworks.reporting import _configuration
    configuration = _configuration(framework)
    return HistoricalSourceSetBinding(
        name=name,
        execution_timeframe=configuration.timeframe_roles[configuration.primary_role],
        role_timeframes=configuration.timeframe_roles,
        sources=sources,
        applicable_frameworks=(framework,),
    )


def campaign_config(root, framework="ema_ribbon_trend", source_name="local", ranges=None, **overrides):
    values = {
        "campaign_name": "test_campaign",
        "framework_configuration_names": (framework,),
        "source_set_names": (source_name,),
        "research_ranges": tuple(ranges or (HistoricalResearchRange("full"),)),
        "chunk_size_rows": 20,
        "output_root": str(root),
    }
    values.update(overrides)
    return HistoricalCampaignConfig(**values)


def all_35_bindings(rows: int = 20):
    names = trading_framework_registry.list_names()
    intraday = []
    groups = {
        "hourly_1h": ("donchian_breakout",),
        "four_hour_4h": ("ichimoku_cloud_trading",),
        "daily_1d": ("turtle_trading",),
        "multi_timeframe": ("triple_screen_trading",),
    }
    special = {name for values in groups.values() for name in values}
    intraday.extend(name for name in names if name not in special)
    result = {}
    representatives = {
        "intraday_15m": "ema_ribbon_trend",
        "hourly_1h": "donchian_breakout",
        "four_hour_4h": "ichimoku_cloud_trading",
        "daily_1d": "turtle_trading",
        "multi_timeframe": "triple_screen_trading",
    }
    applicable = {"intraday_15m": tuple(intraday), **groups}
    for source_name, representative in representatives.items():
        base = binding_for(source_name, representative, rows)
        result[source_name] = HistoricalSourceSetBinding(
            base.name,
            base.execution_timeframe,
            base.role_timeframes,
            base.sources,
            applicable_frameworks=applicable[source_name],
        )
    return result
