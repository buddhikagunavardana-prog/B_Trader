from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.exceptions import FrameworkNotFoundError


VALID_CATEGORIES = {"multi_timeframe", "trend_following", "mean_reversion", "breakout", "momentum", "price_action"}


def _normalize(name: str) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


class TradingFrameworkRegistry:
    def __init__(self) -> None:
        self._classes: dict[str, type[BaseTradingFramework]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, framework_class: type[BaseTradingFramework]) -> None:
        if not issubclass(framework_class, BaseTradingFramework):
            raise TypeError("registered framework must inherit BaseTradingFramework")
        metadata = framework_class.schema.metadata
        name = _normalize(metadata.name)
        if name != metadata.name:
            raise ValueError(f"framework name must be canonical snake_case: {metadata.name}")
        if metadata.category not in VALID_CATEGORIES:
            raise ValueError(f"unsupported framework category: {metadata.category}")
        if name in self._classes or name in self._aliases:
            raise ValueError(f"duplicate framework name: {name}")
        aliases = {_normalize(alias) for alias in metadata.aliases}
        collisions = sorted(aliases & (set(self._classes) | set(self._aliases) | {name}))
        if collisions:
            raise ValueError(f"duplicate framework aliases: {', '.join(collisions)}")
        self._classes[name] = framework_class
        self._aliases.update({alias: name for alias in aliases})

    def canonical_name(self, name: str) -> str:
        key = _normalize(name)
        canonical = self._aliases.get(key, key)
        if canonical not in self._classes:
            raise FrameworkNotFoundError(f"Trading framework not found: {name}")
        return canonical

    def resolve(self, name: str) -> type[BaseTradingFramework]:
        return self._classes[self.canonical_name(name)]

    def get(self, name: str) -> dict[str, Any]:
        framework_class = self.resolve(name)
        source = inspect.getsourcefile(framework_class) or ""
        return {
            "name": framework_class.schema.metadata.name,
            "metadata": framework_class.schema.metadata.to_dict(),
            "schema": framework_class.schema.to_dict(),
            "source_file": Path(source).as_posix(),
        }

    def list_names(self) -> list[str]:
        return sorted(self._classes)

    def list_categories(self) -> list[str]:
        return sorted({item.schema.metadata.category for item in self._classes.values()})

    def list_by_category(self, category: str) -> list[str]:
        return sorted(
            name for name, item in self._classes.items()
            if item.schema.metadata.category == category
        )

    def list_by_market(self, market: str) -> list[str]:
        return sorted(name for name, item in self._classes.items() if market in item.schema.metadata.supported_markets)

    def list_by_timeframe(self, timeframe: str) -> list[str]:
        return sorted(name for name, item in self._classes.items() if timeframe in item.schema.metadata.supported_timeframes)

    def list_stable(self) -> list[str]:
        return sorted(name for name, item in self._classes.items() if item.schema.metadata.stability.value == "stable")

    def list_definitions(self) -> list[dict[str, Any]]:
        return [self.get(name) for name in self.list_names()]


trading_framework_registry = TradingFrameworkRegistry()


def _register_defaults() -> None:
    from src.trading_frameworks.breakout.donchian_breakout import DonchianBreakoutFramework
    from src.trading_frameworks.mean_reversion.bollinger_mean_reversion import BollingerMeanReversionFramework
    from src.trading_frameworks.multi_timeframe.triple_screen import TripleScreenTradingFramework
    from src.trading_frameworks.trend_following.ichimoku_cloud import IchimokuCloudTradingFramework
    from src.trading_frameworks.trend_following.turtle import TurtleTradingFramework
    from src.trading_frameworks.trend_following.expansion import SupertrendTrendFollowingFramework, EmaRibbonTrendFramework, DualMovingAverageCrossoverFramework, AdxTrendFollowingFramework, ParabolicSarTrendFramework
    from src.trading_frameworks.breakout.expansion import BollingerSqueezeBreakoutFramework, KeltnerChannelBreakoutFramework, AtrVolatilityBreakoutFramework, OpeningRangeBreakoutFramework
    from src.trading_frameworks.momentum.expansion import RsiPullbackTrendFramework, MacdMomentumFramework
    from src.trading_frameworks.mean_reversion.expansion import VwapMeanReversionFramework, ZscoreMeanReversionFramework
    from src.trading_frameworks.price_action.expansion import InsideBarBreakoutFramework, SupportResistanceBounceFramework
    from src.trading_frameworks.momentum.professional import ElderImpulseSystemFramework, StochasticPullbackTrendFramework, CciTrendPullbackFramework
    from src.trading_frameworks.mean_reversion.professional import ConnorsRsiMeanReversionFramework, WilliamsRReversalFramework
    from src.trading_frameworks.trend_following.professional import ChandelierExitTrendFramework, PriceChannelTrendFramework, HeikinAshiTrendFramework, AroonTrendFramework
    from src.trading_frameworks.breakout.professional import MomentumAccelerationBreakoutFramework, VolumeExpansionBreakoutFramework, PivotRangeBreakoutFramework
    from src.trading_frameworks.price_action.professional import Nr4Nr7VolatilityBreakoutFramework, PinBarRejectionFramework, EngulfingConfirmationTrendFramework

    for framework in (
        TripleScreenTradingFramework,
        TurtleTradingFramework,
        IchimokuCloudTradingFramework,
        BollingerMeanReversionFramework,
        DonchianBreakoutFramework,
        SupertrendTrendFollowingFramework, EmaRibbonTrendFramework,
        DualMovingAverageCrossoverFramework, AdxTrendFollowingFramework,
        ParabolicSarTrendFramework, BollingerSqueezeBreakoutFramework,
        KeltnerChannelBreakoutFramework, AtrVolatilityBreakoutFramework,
        OpeningRangeBreakoutFramework, RsiPullbackTrendFramework,
        MacdMomentumFramework, VwapMeanReversionFramework,
        ZscoreMeanReversionFramework, InsideBarBreakoutFramework,
        SupportResistanceBounceFramework,
        ElderImpulseSystemFramework, ConnorsRsiMeanReversionFramework,
        StochasticPullbackTrendFramework, WilliamsRReversalFramework,
        CciTrendPullbackFramework, ChandelierExitTrendFramework,
        PriceChannelTrendFramework, HeikinAshiTrendFramework, AroonTrendFramework,
        MomentumAccelerationBreakoutFramework, VolumeExpansionBreakoutFramework,
        Nr4Nr7VolatilityBreakoutFramework, PinBarRejectionFramework,
        EngulfingConfirmationTrendFramework, PivotRangeBreakoutFramework,
    ):
        trading_framework_registry.register(framework)


_register_defaults()


def get_framework(name: str) -> dict[str, Any]:
    return trading_framework_registry.get(name)


def list_frameworks() -> list[str]:
    return trading_framework_registry.list_names()


def list_frameworks_by_category(category: str) -> list[str]:
    return trading_framework_registry.list_by_category(category)


def list_frameworks_by_market(market: str) -> list[str]:
    return trading_framework_registry.list_by_market(market)


def list_frameworks_by_timeframe(timeframe: str) -> list[str]:
    return trading_framework_registry.list_by_timeframe(timeframe)


def list_stable_frameworks() -> list[str]:
    return trading_framework_registry.list_stable()
