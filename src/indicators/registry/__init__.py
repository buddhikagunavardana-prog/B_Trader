from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.indicators.candlestick.candlestick import calculate_candlestick_patterns
from src.indicators.market_strength.adx import calculate_adx
from src.indicators.market_strength.aroon import calculate_aroon
from src.indicators.market_strength.choppiness import calculate_choppiness_index
from src.indicators.market_strength.dmi import calculate_dmi
from src.indicators.market_strength.elder_ray import calculate_elder_ray
from src.indicators.market_strength.vortex import calculate_vortex
from src.indicators.momentum.cci import calculate_cci
from src.indicators.momentum.macd import calculate_macd
from src.indicators.momentum.momentum import calculate_momentum
from src.indicators.momentum.roc import calculate_roc
from src.indicators.momentum.rsi import calculate_rsi
from src.indicators.momentum.stochastic import calculate_stochastic
from src.indicators.momentum.stochastic_rsi import calculate_stochastic_rsi
from src.indicators.momentum.tsi import calculate_tsi
from src.indicators.momentum.ultimate_oscillator import calculate_ultimate_oscillator
from src.indicators.momentum.williams_r import calculate_williams_r
from src.indicators.structure.fibonacci_retracement import calculate_fibonacci_retracement
from src.indicators.structure.linear_regression_channel import calculate_linear_regression_channel
from src.indicators.structure.pivot_points import calculate_pivot_points
from src.indicators.structure.price_channels import calculate_price_channels
from src.indicators.structure.support_resistance import calculate_support_resistance
from src.indicators.structure.swing import calculate_swing_points
from src.indicators.trend.dema import calculate_dema
from src.indicators.trend.ema import calculate_ema
from src.indicators.trend.hma import calculate_hma
from src.indicators.trend.ichimoku import calculate_ichimoku_cloud
from src.indicators.trend.kama import calculate_kama
from src.indicators.trend.sma import calculate_sma
from src.indicators.trend.supertrend import calculate_supertrend
from src.indicators.trend.tema import calculate_tema
from src.indicators.trend.vwma import calculate_vwma
from src.indicators.trend.wma import calculate_wma
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.bollinger import calculate_bollinger
from src.indicators.volatility.chaikin import calculate_chaikin_volatility
from src.indicators.volatility.donchian import calculate_donchian_channel
from src.indicators.volatility.historical_volatility import calculate_historical_volatility
from src.indicators.volatility.keltner import calculate_keltner_channel
from src.indicators.volatility.standard_deviation import calculate_standard_deviation
from src.indicators.volume.adl import calculate_adl
from src.indicators.volume.cmf import calculate_cmf
from src.indicators.volume.ease_of_movement import calculate_ease_of_movement
from src.indicators.volume.mfi import calculate_mfi
from src.indicators.volume.obv import calculate_obv
from src.indicators.volume.volume_roc import calculate_volume_roc
from src.indicators.volume.volume import calculate_volume_sma
from src.indicators.volume.vwap import calculate_vwap


@dataclass(frozen=True)
class IndicatorDefinition:
    name: str
    category: str
    function: Callable
    default_params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "function": self.function,
            "default_params": dict(self.default_params),
        }


class IndicatorRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, IndicatorDefinition] = {}

    def register(
        self,
        name: str,
        category: str,
        function: Callable,
        default_params: dict[str, Any] | None = None,
    ) -> None:
        key = self._normalize(name)
        if not key or not callable(function):
            raise ValueError("indicator name and callable function are required")
        if key in self._definitions:
            raise ValueError(f"indicator already registered: {key}")
        definition = IndicatorDefinition(
            name=key,
            category=str(category).strip().lower(),
            function=function,
            default_params=dict(default_params or {}),
        )
        self._validate_signature(definition, definition.default_params)
        self._definitions[key] = definition

    def get(self, name: str) -> dict[str, Any]:
        key = self._normalize(name)
        if key not in self._definitions:
            raise ValueError(f"Indicator not found in registry: {name}")
        return self._definitions[key].to_dict()

    def list_names(self) -> list[str]:
        return list(self._definitions)

    def list_categories(self) -> list[str]:
        return sorted({item.category for item in self._definitions.values()})

    def list_by_category(self, category: str) -> list[str]:
        normalized = str(category).strip().lower()
        return [
            item.name for item in self._definitions.values()
            if item.category == normalized
        ]

    def validate_parameters(self, name: str, params: dict[str, Any] | None) -> dict[str, Any]:
        definition = self._definitions.get(self._normalize(name))
        if definition is None:
            raise ValueError(f"Indicator not found in registry: {name}")
        if params is not None and not isinstance(params, dict):
            raise ValueError(f"indicator parameters must be a dictionary: {name}")
        merged = dict(definition.default_params)
        merged.update(params or {})
        self._validate_signature(definition, merged)
        for key, value in merged.items():
            if key == "source":
                if not isinstance(value, str) or not value:
                    raise ValueError("source must be a non-empty column name")
            elif key.endswith("period") or key in {
                "period", "displacement", "fast", "slow", "signal",
            }:
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ValueError(f"{key} must be a positive integer")
            elif key in {"multiplier", "std_dev", "deviations", "annualization", "volume_divisor"}:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                    raise ValueError(f"{key} must be positive")
        return merged

    def calculate(
        self,
        name: str,
        df: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> Any:
        definition = self._definitions.get(self._normalize(name))
        if definition is None:
            raise ValueError(f"Indicator not found in registry: {name}")
        return definition.function(df, **self.validate_parameters(name, params))

    @staticmethod
    def _normalize(name: str) -> str:
        key = str(name).strip().lower().replace(" ", "_")
        return {
            "bollinger": "bollinger_bands",
            "keltner": "keltner_channel",
            "donchian": "donchian_channel",
            "volume": "volume_sma",
            "adl": "accumulation_distribution",
            "swing": "swing_high_low",
            "fibonacci": "fibonacci_retracement",
        }.get(key, key)

    @staticmethod
    def _validate_signature(
        definition: IndicatorDefinition,
        params: dict[str, Any],
    ) -> None:
        try:
            inspect.signature(definition.function).bind_partial(None, **params)
        except TypeError as error:
            raise ValueError(
                f"invalid parameters for indicator {definition.name}: {error}",
            ) from error


indicator_registry = IndicatorRegistry()


def _register_defaults() -> None:
    definitions = [
        ("ema", "trend", calculate_ema, {"period": 20, "source": "close"}),
        ("sma", "trend", calculate_sma, {"period": 20, "source": "close"}),
        ("wma", "trend", calculate_wma, {"period": 20, "source": "close"}),
        ("vwma", "trend", calculate_vwma, {"period": 20, "source": "close"}),
        ("hma", "trend", calculate_hma, {"period": 20, "source": "close"}),
        ("dema", "trend", calculate_dema, {"period": 20, "source": "close"}),
        ("tema", "trend", calculate_tema, {"period": 20, "source": "close"}),
        ("kama", "trend", calculate_kama, {"period": 10, "fast_period": 2, "slow_period": 30, "source": "close"}),
        ("supertrend", "trend", calculate_supertrend, {"period": 10, "multiplier": 3.0}),
        ("ichimoku_cloud", "trend", calculate_ichimoku_cloud, {"conversion_period": 9, "base_period": 26, "span_b_period": 52, "displacement": 26}),
        ("rsi", "momentum", calculate_rsi, {"period": 14}),
        ("macd", "momentum", calculate_macd, {"fast": 12, "slow": 26, "signal": 9}),
        ("stochastic", "momentum", calculate_stochastic, {"k_period": 14, "d_period": 3}),
        ("stochastic_rsi", "momentum", calculate_stochastic_rsi, {"rsi_period": 14, "stoch_period": 14, "d_period": 3}),
        ("cci", "momentum", calculate_cci, {"period": 20}),
        ("williams_r", "momentum", calculate_williams_r, {"period": 14}),
        ("roc", "momentum", calculate_roc, {"period": 12, "source": "close"}),
        ("momentum", "momentum", calculate_momentum, {"period": 10, "source": "close"}),
        ("tsi", "momentum", calculate_tsi, {"long_period": 25, "short_period": 13, "source": "close"}),
        ("ultimate_oscillator", "momentum", calculate_ultimate_oscillator, {"short_period": 7, "medium_period": 14, "long_period": 28}),
        ("atr", "volatility", calculate_atr, {"period": 14}),
        ("bollinger_bands", "volatility", calculate_bollinger, {"period": 20, "std_dev": 2.0}),
        ("keltner_channel", "volatility", calculate_keltner_channel, {"ema_period": 20, "atr_period": 10, "multiplier": 2.0}),
        ("donchian_channel", "volatility", calculate_donchian_channel, {"period": 20}),
        ("historical_volatility", "volatility", calculate_historical_volatility, {"period": 20, "annualization": 365.0, "source": "close"}),
        ("standard_deviation", "volatility", calculate_standard_deviation, {"period": 20, "source": "close"}),
        ("chaikin_volatility", "volatility", calculate_chaikin_volatility, {"ema_period": 10, "roc_period": 10}),
        ("obv", "volume", calculate_obv, {}),
        ("vwap", "volume", calculate_vwap, {}),
        ("cmf", "volume", calculate_cmf, {"period": 20}),
        ("mfi", "volume", calculate_mfi, {"period": 14}),
        ("accumulation_distribution", "volume", calculate_adl, {}),
        ("volume_roc", "volume", calculate_volume_roc, {"period": 12}),
        ("ease_of_movement", "volume", calculate_ease_of_movement, {"period": 14, "volume_divisor": 100000000.0}),
        ("volume_sma", "volume", calculate_volume_sma, {"period": 20}),
        ("adx", "market_strength", calculate_adx, {"period": 14}),
        ("aroon", "market_strength", calculate_aroon, {"period": 25}),
        ("vortex", "market_strength", calculate_vortex, {"period": 14}),
        ("choppiness_index", "market_strength", calculate_choppiness_index, {"period": 14}),
        ("dmi", "market_strength", calculate_dmi, {"period": 14}),
        ("elder_ray_index", "market_strength", calculate_elder_ray, {"period": 13}),
        ("pivot_points", "structure", calculate_pivot_points, {}),
        ("support_resistance", "structure", calculate_support_resistance, {"period": 20}),
        ("swing_high_low", "structure", calculate_swing_points, {"period": 5}),
        ("price_channels", "structure", calculate_price_channels, {"period": 20}),
        ("fibonacci_retracement", "structure", calculate_fibonacci_retracement, {"period": 20}),
        ("linear_regression_channel", "structure", calculate_linear_regression_channel, {"period": 20, "deviations": 2.0, "source": "close"}),
        ("candlestick", "candlestick", calculate_candlestick_patterns, {}),
    ]
    for name, category, function, defaults in definitions:
        indicator_registry.register(name, category, function, defaults)


_register_defaults()
INDICATOR_REGISTRY = {
    name: indicator_registry.get(name)["function"]
    for name in indicator_registry.list_names()
}


def get_indicator(name: str) -> Callable:
    return indicator_registry.get(name)["function"]


def list_indicators() -> list[str]:
    return indicator_registry.list_names()
