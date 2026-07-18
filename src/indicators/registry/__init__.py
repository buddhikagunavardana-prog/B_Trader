from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.indicators._validation import require_columns
from src.indicators.candlestick.candlestick import calculate_candlestick_patterns
from src.indicators.market_strength.adx import calculate_adx
from src.indicators.market_strength.aroon import calculate_aroon
from src.indicators.market_strength.choppiness import calculate_choppiness_index
from src.indicators.market_strength.directional import calculate_minus_di, calculate_plus_di
from src.indicators.market_strength.dmi import calculate_dmi
from src.indicators.market_strength.elder_ray import calculate_elder_ray
from src.indicators.market_strength.vortex import calculate_vortex
from src.indicators.momentum.cci import calculate_cci
from src.indicators.momentum.advanced import (
    calculate_apo,
    calculate_awesome_oscillator,
    calculate_balance_of_power,
    calculate_cmo,
    calculate_connors_rsi,
    calculate_coppock_curve,
    calculate_fisher_transform,
    calculate_ppo,
    calculate_rmi,
    calculate_trix,
)
from src.indicators.momentum.macd import calculate_macd
from src.indicators.momentum.momentum import calculate_momentum
from src.indicators.momentum.roc import calculate_roc
from src.indicators.momentum.rsi import calculate_rsi
from src.indicators.momentum.stochastic import calculate_stochastic
from src.indicators.momentum.stochastic_rsi import calculate_stochastic_rsi
from src.indicators.momentum.tsi import calculate_tsi
from src.indicators.momentum.ultimate_oscillator import calculate_ultimate_oscillator
from src.indicators.momentum.williams_r import calculate_williams_r
from src.indicators.momentum.zscore import calculate_zscore
from src.indicators.structure.fibonacci_retracement import calculate_fibonacci_retracement
from src.indicators.structure.breakout import calculate_breakout_detection
from src.indicators.structure.linear_regression_channel import calculate_linear_regression_channel
from src.indicators.structure.pivot_points import calculate_pivot_points
from src.indicators.structure.price_channels import calculate_price_channels
from src.indicators.structure.support_resistance import calculate_support_resistance
from src.indicators.structure.swing import calculate_swing_points
from src.indicators.structure.smc import (
    calculate_fair_value_gap,
    calculate_market_structure,
    calculate_order_block,
)
from src.indicators.trend.advanced import (
    calculate_alma,
    calculate_dpo,
    calculate_frama,
    calculate_linear_regression_slope,
    calculate_linear_regression_trend,
    calculate_mcginley_dynamic,
    calculate_moving_average_envelope,
    calculate_time_series_forecast,
    calculate_trima,
    calculate_vidya,
    calculate_zlema,
)
from src.indicators.trend.dema import calculate_dema
from src.indicators.trend.ema import calculate_ema
from src.indicators.trend.hma import calculate_hma
from src.indicators.trend.ichimoku import calculate_ichimoku_cloud
from src.indicators.trend.kama import calculate_kama
from src.indicators.trend.parabolic_sar import calculate_parabolic_sar
from src.indicators.trend.sma import calculate_sma
from src.indicators.trend.supertrend import calculate_supertrend
from src.indicators.trend.tema import calculate_tema
from src.indicators.trend.vwma import calculate_vwma
from src.indicators.trend.wma import calculate_wma
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.advanced import (
    calculate_bollinger_band_width,
    calculate_bollinger_percent_b,
    calculate_chandelier_exit,
    calculate_mass_index,
    calculate_normalized_atr,
    calculate_ulcer_index,
)
from src.indicators.volatility.bollinger import calculate_bollinger
from src.indicators.volatility.chaikin import calculate_chaikin_volatility
from src.indicators.volatility.donchian import calculate_donchian_channel
from src.indicators.volatility.historical_volatility import calculate_historical_volatility
from src.indicators.volatility.keltner import calculate_keltner_channel
from src.indicators.volatility.standard_deviation import calculate_standard_deviation
from src.indicators.volume.adl import calculate_adl
from src.indicators.volume.advanced import (
    calculate_chaikin_oscillator,
    calculate_force_index,
    calculate_negative_volume_index,
    calculate_positive_volume_index,
    calculate_volume_ema,
)
from src.indicators.volume.cmf import calculate_cmf
from src.indicators.volume.ease_of_movement import calculate_ease_of_movement
from src.indicators.volume.mfi import calculate_mfi
from src.indicators.volume.obv import calculate_obv
from src.indicators.volume.volume_roc import calculate_volume_roc
from src.indicators.volume.rolling_vwap import calculate_rolling_vwap
from src.indicators.volume.volume import calculate_volume_sma
from src.indicators.volume.vwap import calculate_vwap


@dataclass(frozen=True)
class IndicatorDefinition:
    name: str
    category: str
    function: Callable
    default_params: dict[str, Any]
    required_columns: tuple[str, ...]
    output_columns: tuple[str, ...]
    description: str
    dependencies: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "function": self.function,
            "callable": self.function,
            "default_params": dict(self.default_params),
            "default_parameters": dict(self.default_params),
            "required_columns": list(self.required_columns),
            "output_columns": list(self.output_columns),
            "description": self.description,
            "dependencies": list(self.dependencies),
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
        *,
        required_columns: tuple[str, ...] = (),
        output_columns: tuple[str, ...] = (),
        description: str = "",
        dependencies: tuple[str, ...] = (),
    ) -> None:
        key = self._normalize(name)
        if not key or not callable(function):
            raise ValueError("indicator name and callable function are required")
        if key in self._definitions:
            raise ValueError(f"indicator already registered: {key}")
        normalized_category = str(category).strip().lower()
        if not normalized_category:
            raise ValueError("indicator category is required")
        if output_columns and len(set(output_columns)) != len(output_columns):
            raise ValueError(f"output columns must be unique: {key}")
        if any(not str(column).strip() for column in required_columns):
            raise ValueError(f"required columns must be non-empty: {key}")
        definition = IndicatorDefinition(
            name=key,
            category=normalized_category,
            function=function,
            default_params=dict(default_params or {}),
            required_columns=tuple(required_columns),
            # Preserve the original four-argument registration API while
            # giving older callers a predictable single-output convention.
            output_columns=tuple(output_columns) or (key.upper(),),
            description=str(description).strip() or f"Calculate {key.replace('_', ' ')}.",
            dependencies=tuple(self._normalize(item) for item in dependencies),
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
            elif key in {
                "multiplier", "std_dev", "deviations", "annualization",
                "volume_divisor", "acceleration", "maximum",
            }:
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
        require_columns(df, definition.required_columns)
        self._validate_dependencies(definition)
        output = definition.function(df, **self.validate_parameters(name, params))
        return self._standardize_output(definition, output, df.index)

    def validate_dependencies(self) -> None:
        """Verify that all declared indicator dependencies are registered."""
        for definition in self._definitions.values():
            self._validate_dependencies(definition)

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

    def _validate_dependencies(self, definition: IndicatorDefinition) -> None:
        missing = [
            dependency for dependency in definition.dependencies
            if dependency not in self._definitions
        ]
        if missing:
            raise ValueError(
                f"indicator {definition.name} has unregistered dependencies: {missing}",
            )

    @staticmethod
    def _standardize_output(
        definition: IndicatorDefinition,
        output: Any,
        index: pd.Index,
    ) -> Any:
        expected = definition.output_columns

        def normalize_series(series: pd.Series, column: str) -> pd.Series:
            if not isinstance(series, pd.Series) or not series.index.equals(index):
                raise ValueError(
                    f"indicator {definition.name} returned a misaligned output",
                )
            result = series.rename(column)
            if pd.api.types.is_numeric_dtype(result.dtype):
                result = result.replace([float("inf"), float("-inf")], float("nan"))
            return result

        if isinstance(output, pd.Series):
            if len(expected) != 1:
                raise ValueError(f"indicator {definition.name} output count mismatch")
            return normalize_series(output, expected[0])
        if isinstance(output, pd.DataFrame):
            if not output.index.equals(index) or tuple(output.columns) != expected:
                raise ValueError(f"indicator {definition.name} output columns mismatch")
            result = output.copy()
            numeric = result.select_dtypes(include="number").columns
            result[numeric] = result[numeric].replace(
                [float("inf"), float("-inf")], float("nan"),
            )
            return result
        if isinstance(output, (tuple, list)):
            if len(output) != len(expected):
                raise ValueError(f"indicator {definition.name} output count mismatch")
            values = [
                normalize_series(series, column)
                for series, column in zip(output, expected)
            ]
            return tuple(values) if isinstance(output, tuple) else values
        if isinstance(output, dict):
            if len(output) != len(expected):
                raise ValueError(f"indicator {definition.name} output count mismatch")
            return {
                key: normalize_series(series, column)
                for (key, series), column in zip(output.items(), expected)
            }
        raise ValueError(
            f"indicator {definition.name} returned unsupported output {type(output)!r}",
        )


indicator_registry = IndicatorRegistry()


_INDICATOR_METADATA: dict[str, dict[str, tuple[str, ...]]] = {
    "ema": {"required_columns": ("close",), "output_columns": ("EMA",)},
    "sma": {"required_columns": ("close",), "output_columns": ("SMA",)},
    "wma": {"required_columns": ("close",), "output_columns": ("WMA",)},
    "vwma": {"required_columns": ("close", "volume"), "output_columns": ("VWMA",)},
    "hma": {"required_columns": ("close",), "output_columns": ("HMA",)},
    "dema": {"required_columns": ("close",), "output_columns": ("DEMA",)},
    "tema": {"required_columns": ("close",), "output_columns": ("TEMA",)},
    "kama": {"required_columns": ("close",), "output_columns": ("KAMA",)},
    "supertrend": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("SUPERTREND", "SUPERTREND_DIRECTION"),
        "dependencies": ("atr",),
    },
    "ichimoku_cloud": {
        "required_columns": ("high", "low", "close"),
        "output_columns": (
            "ICHIMOKU_CONVERSION", "ICHIMOKU_BASE", "ICHIMOKU_SPAN_A",
            "ICHIMOKU_SPAN_B", "ICHIMOKU_LAGGING",
        ),
    },
    "parabolic_sar": {
        "required_columns": ("high", "low"),
        "output_columns": ("PARABOLIC_SAR", "PARABOLIC_SAR_DIRECTION"),
    },
    "rsi": {"required_columns": ("close",), "output_columns": ("RSI",)},
    "macd": {
        "required_columns": ("close",),
        "output_columns": ("MACD", "MACD_SIGNAL", "MACD_HISTOGRAM"),
    },
    "stochastic": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("STOCHASTIC_K", "STOCHASTIC_D"),
    },
    "stochastic_rsi": {
        "required_columns": ("close",),
        "output_columns": ("STOCHASTIC_RSI_K", "STOCHASTIC_RSI_D"),
        "dependencies": ("rsi",),
    },
    "cci": {"required_columns": ("high", "low", "close"), "output_columns": ("CCI",)},
    "williams_r": {"required_columns": ("high", "low", "close"), "output_columns": ("WILLIAMS_R",)},
    "roc": {"required_columns": ("close",), "output_columns": ("ROC",)},
    "momentum": {"required_columns": ("close",), "output_columns": ("MOMENTUM",)},
    "tsi": {"required_columns": ("close",), "output_columns": ("TSI",)},
    "ultimate_oscillator": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("ULTIMATE_OSCILLATOR",),
    },
    "zscore": {"required_columns": ("close",), "output_columns": ("ZSCORE",)},
    "atr": {"required_columns": ("high", "low", "close"), "output_columns": ("ATR",)},
    "bollinger_bands": {
        "required_columns": ("close",),
        "output_columns": ("BOLLINGER_UPPER", "BOLLINGER_MIDDLE", "BOLLINGER_LOWER"),
    },
    "keltner_channel": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("KELTNER_UPPER", "KELTNER_MIDDLE", "KELTNER_LOWER"),
        "dependencies": ("ema", "atr"),
    },
    "donchian_channel": {
        "required_columns": ("high", "low"),
        "output_columns": ("DONCHIAN_UPPER", "DONCHIAN_MIDDLE", "DONCHIAN_LOWER"),
    },
    "historical_volatility": {"required_columns": ("close",), "output_columns": ("HISTORICAL_VOLATILITY",)},
    "standard_deviation": {"required_columns": ("close",), "output_columns": ("STANDARD_DEVIATION",)},
    "chaikin_volatility": {"required_columns": ("high", "low"), "output_columns": ("CHAIKIN_VOLATILITY",)},
    "obv": {"required_columns": ("close", "volume"), "output_columns": ("OBV",)},
    "vwap": {"required_columns": ("high", "low", "close", "volume"), "output_columns": ("VWAP",)},
    "cmf": {"required_columns": ("high", "low", "close", "volume"), "output_columns": ("CMF",)},
    "mfi": {"required_columns": ("high", "low", "close", "volume"), "output_columns": ("MFI",)},
    "accumulation_distribution": {
        "required_columns": ("high", "low", "close", "volume"),
        "output_columns": ("ACCUMULATION_DISTRIBUTION",),
    },
    "volume_roc": {"required_columns": ("volume",), "output_columns": ("VOLUME_ROC",)},
    "ease_of_movement": {"required_columns": ("high", "low", "volume"), "output_columns": ("EASE_OF_MOVEMENT",)},
    "volume_sma": {"required_columns": ("volume",), "output_columns": ("VOLUME_SMA",)},
    "rolling_vwap": {
        "required_columns": ("high", "low", "close", "volume"),
        "output_columns": ("ROLLING_VWAP",),
    },
    "adx": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("ADX",),
        "dependencies": ("dmi",),
    },
    "aroon": {"required_columns": ("high", "low"), "output_columns": ("AROON_UP", "AROON_DOWN")},
    "vortex": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("VORTEX_POSITIVE", "VORTEX_NEGATIVE"),
    },
    "choppiness_index": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("CHOPPINESS_INDEX",),
    },
    "dmi": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("DMI_PLUS", "DMI_MINUS"),
        "dependencies": ("atr",),
    },
    "elder_ray_index": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("BULL_POWER", "BEAR_POWER"),
        "dependencies": ("ema",),
    },
    "pivot_points": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("PIVOT", "PIVOT_R1", "PIVOT_R2", "PIVOT_R3", "PIVOT_S1", "PIVOT_S2", "PIVOT_S3"),
    },
    "support_resistance": {
        "required_columns": ("high", "low"),
        "output_columns": ("SUPPORT", "RESISTANCE"),
    },
    "swing_high_low": {"required_columns": ("high", "low"), "output_columns": ("SWING_HIGH", "SWING_LOW")},
    "price_channels": {
        "required_columns": ("high", "low"),
        "output_columns": ("PRICE_CHANNEL_UPPER", "PRICE_CHANNEL_MIDDLE", "PRICE_CHANNEL_LOWER"),
    },
    "fibonacci_retracement": {
        "required_columns": ("high", "low"),
        "output_columns": (
            "FIBONACCI_0_0", "FIBONACCI_23_6", "FIBONACCI_38_2", "FIBONACCI_50_0",
            "FIBONACCI_61_8", "FIBONACCI_78_6", "FIBONACCI_100_0",
        ),
    },
    "linear_regression_channel": {
        "required_columns": ("close",),
        "output_columns": (
            "LINEAR_REGRESSION_UPPER", "LINEAR_REGRESSION_MIDDLE", "LINEAR_REGRESSION_LOWER",
        ),
    },
    "candlestick": {
        "required_columns": ("open", "high", "low", "close"),
        "output_columns": (
            "doji", "dragonfly_doji", "gravestone_doji", "hammer", "hanging_man",
            "inverted_hammer", "shooting_star", "bullish_engulfing", "bearish_engulfing",
            "bullish_harami", "bearish_harami", "morning_star", "evening_star",
            "bullish_marubozu", "bearish_marubozu", "spinning_top", "tweezer_bottom",
            "tweezer_top", "piercing_line", "dark_cloud_cover", "three_white_soldiers",
            "three_black_crows", "inside_bar", "outside_bar", "gap_up", "gap_down",
        ),
    },
}

_INDICATOR_METADATA.update({
    "linear_regression_trend": {
        "required_columns": ("close",),
        "output_columns": ("LINEAR_REGRESSION_TREND",),
    },
    "trima": {"required_columns": ("close",), "output_columns": ("TRIMA",), "dependencies": ("sma",)},
    "alma": {"required_columns": ("close",), "output_columns": ("ALMA",)},
    "zlema": {"required_columns": ("close",), "output_columns": ("ZLEMA",), "dependencies": ("ema",)},
    "mcginley_dynamic": {"required_columns": ("close",), "output_columns": ("MCGINLEY_DYNAMIC",)},
    "frama": {"required_columns": ("high", "low", "close"), "output_columns": ("FRAMA",)},
    "vidya": {"required_columns": ("close",), "output_columns": ("VIDYA",), "dependencies": ("cmo",)},
    "moving_average_envelope": {
        "required_columns": ("close",),
        "output_columns": ("MA_ENVELOPE_UPPER", "MA_ENVELOPE_MIDDLE", "MA_ENVELOPE_LOWER"),
        "dependencies": ("sma",),
    },
    "linear_regression_slope": {"required_columns": ("close",), "output_columns": ("LINEAR_REGRESSION_SLOPE",)},
    "time_series_forecast": {"required_columns": ("close",), "output_columns": ("TIME_SERIES_FORECAST",)},
    "dpo": {"required_columns": ("close",), "output_columns": ("DPO",), "dependencies": ("sma",)},
    "trix": {"required_columns": ("close",), "output_columns": ("TRIX",), "dependencies": ("ema",)},
    "ppo": {
        "required_columns": ("close",),
        "output_columns": ("PPO", "PPO_SIGNAL", "PPO_HISTOGRAM"),
        "dependencies": ("ema",),
    },
    "apo": {"required_columns": ("close",), "output_columns": ("APO",), "dependencies": ("ema",)},
    "cmo": {"required_columns": ("close",), "output_columns": ("CMO",)},
    "connors_rsi": {"required_columns": ("close",), "output_columns": ("CONNORS_RSI",), "dependencies": ("rsi",)},
    "rmi": {"required_columns": ("close",), "output_columns": ("RMI",)},
    "fisher_transform": {"required_columns": ("high", "low"), "output_columns": ("FISHER_TRANSFORM",)},
    "awesome_oscillator": {"required_columns": ("high", "low"), "output_columns": ("AWESOME_OSCILLATOR",)},
    "balance_of_power": {"required_columns": ("open", "high", "low", "close"), "output_columns": ("BALANCE_OF_POWER",)},
    "coppock_curve": {"required_columns": ("close",), "output_columns": ("COPPOCK_CURVE",)},
    "bollinger_band_width": {
        "required_columns": ("close",),
        "output_columns": ("BOLLINGER_BAND_WIDTH",),
        "dependencies": ("bollinger_bands",),
    },
    "bollinger_percent_b": {
        "required_columns": ("close",),
        "output_columns": ("BOLLINGER_PERCENT_B",),
        "dependencies": ("bollinger_bands",),
    },
    "chandelier_exit": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("CHANDELIER_LONG", "CHANDELIER_SHORT"),
        "dependencies": ("atr",),
    },
    "normalized_atr": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("NORMALIZED_ATR",),
        "dependencies": ("atr",),
    },
    "ulcer_index": {"required_columns": ("close",), "output_columns": ("ULCER_INDEX",)},
    "mass_index": {"required_columns": ("high", "low"), "output_columns": ("MASS_INDEX",)},
    "force_index": {"required_columns": ("close", "volume"), "output_columns": ("FORCE_INDEX",)},
    "volume_ema": {"required_columns": ("volume",), "output_columns": ("VOLUME_EMA",)},
    "chaikin_oscillator": {
        "required_columns": ("high", "low", "close", "volume"),
        "output_columns": ("CHAIKIN_OSCILLATOR",),
        "dependencies": ("accumulation_distribution", "ema"),
    },
    "negative_volume_index": {"required_columns": ("close", "volume"), "output_columns": ("NEGATIVE_VOLUME_INDEX",)},
    "positive_volume_index": {"required_columns": ("close", "volume"), "output_columns": ("POSITIVE_VOLUME_INDEX",)},
    "plus_di": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("PLUS_DI",),
        "dependencies": ("dmi",),
    },
    "minus_di": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("MINUS_DI",),
        "dependencies": ("dmi",),
    },
    "breakout_detection": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("BREAKOUT_UPPER", "BREAKOUT_LOWER", "BREAKOUT_BULLISH", "BREAKOUT_BEARISH"),
    },
    "fair_value_gap": {
        "required_columns": ("high", "low"),
        "output_columns": ("FVG_BULLISH", "FVG_BEARISH", "FVG_LOWER", "FVG_UPPER"),
    },
    "order_block": {
        "required_columns": ("open", "high", "low", "close"),
        "output_columns": ("ORDER_BLOCK_BULLISH", "ORDER_BLOCK_BEARISH", "ORDER_BLOCK_LOWER", "ORDER_BLOCK_UPPER"),
    },
    "market_structure": {
        "required_columns": ("high", "low", "close"),
        "output_columns": ("BOS", "CHOCH", "MARKET_STRUCTURE_TREND"),
    },
})


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
        ("parabolic_sar", "trend", calculate_parabolic_sar, {"acceleration": 0.02, "maximum": 0.2}),
        ("linear_regression_trend", "trend", calculate_linear_regression_trend, {"period": 20, "source": "close"}),
        ("trima", "trend", calculate_trima, {"period": 20, "source": "close"}),
        ("alma", "trend", calculate_alma, {"period": 20, "offset": 0.85, "sigma": 6.0, "source": "close"}),
        ("zlema", "trend", calculate_zlema, {"period": 20, "source": "close"}),
        ("mcginley_dynamic", "trend", calculate_mcginley_dynamic, {"period": 14, "source": "close"}),
        ("frama", "trend", calculate_frama, {"period": 16, "source": "close"}),
        ("vidya", "trend", calculate_vidya, {"period": 14, "momentum_period": 9, "source": "close"}),
        ("moving_average_envelope", "trend", calculate_moving_average_envelope, {"period": 20, "percentage": 2.5, "source": "close"}),
        ("linear_regression_slope", "trend", calculate_linear_regression_slope, {"period": 20, "source": "close"}),
        ("time_series_forecast", "trend", calculate_time_series_forecast, {"period": 20, "source": "close"}),
        ("dpo", "trend", calculate_dpo, {"period": 20, "source": "close"}),
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
        ("zscore", "momentum", calculate_zscore, {"period": 20, "source": "close"}),
        ("trix", "momentum", calculate_trix, {"period": 15, "source": "close"}),
        ("ppo", "momentum", calculate_ppo, {"fast_period": 12, "slow_period": 26, "signal_period": 9, "source": "close"}),
        ("apo", "momentum", calculate_apo, {"fast_period": 12, "slow_period": 26, "source": "close"}),
        ("cmo", "momentum", calculate_cmo, {"period": 14, "source": "close"}),
        ("connors_rsi", "momentum", calculate_connors_rsi, {"rsi_period": 3, "streak_period": 2, "rank_period": 100, "source": "close"}),
        ("rmi", "momentum", calculate_rmi, {"period": 14, "momentum_period": 5, "source": "close"}),
        ("fisher_transform", "momentum", calculate_fisher_transform, {"period": 10}),
        ("awesome_oscillator", "momentum", calculate_awesome_oscillator, {"fast_period": 5, "slow_period": 34}),
        ("balance_of_power", "momentum", calculate_balance_of_power, {}),
        ("coppock_curve", "momentum", calculate_coppock_curve, {"short_period": 11, "long_period": 14, "wma_period": 10, "source": "close"}),
        ("atr", "volatility", calculate_atr, {"period": 14}),
        ("bollinger_bands", "volatility", calculate_bollinger, {"period": 20, "std_dev": 2.0}),
        ("keltner_channel", "volatility", calculate_keltner_channel, {"ema_period": 20, "atr_period": 10, "multiplier": 2.0}),
        ("donchian_channel", "volatility", calculate_donchian_channel, {"period": 20}),
        ("historical_volatility", "volatility", calculate_historical_volatility, {"period": 20, "annualization": 365.0, "source": "close"}),
        ("standard_deviation", "volatility", calculate_standard_deviation, {"period": 20, "source": "close"}),
        ("chaikin_volatility", "volatility", calculate_chaikin_volatility, {"ema_period": 10, "roc_period": 10}),
        ("bollinger_band_width", "volatility", calculate_bollinger_band_width, {"period": 20, "std_dev": 2.0}),
        ("bollinger_percent_b", "volatility", calculate_bollinger_percent_b, {"period": 20, "std_dev": 2.0}),
        ("chandelier_exit", "volatility", calculate_chandelier_exit, {"period": 22, "atr_period": 22, "multiplier": 3.0}),
        ("normalized_atr", "volatility", calculate_normalized_atr, {"period": 14}),
        ("ulcer_index", "volatility", calculate_ulcer_index, {"period": 14, "source": "close"}),
        ("mass_index", "volatility", calculate_mass_index, {"ema_period": 9, "sum_period": 25}),
        ("obv", "volume", calculate_obv, {}),
        ("vwap", "volume", calculate_vwap, {}),
        ("cmf", "volume", calculate_cmf, {"period": 20}),
        ("mfi", "volume", calculate_mfi, {"period": 14}),
        ("accumulation_distribution", "volume", calculate_adl, {}),
        ("volume_roc", "volume", calculate_volume_roc, {"period": 12}),
        ("ease_of_movement", "volume", calculate_ease_of_movement, {"period": 14, "volume_divisor": 100000000.0}),
        ("volume_sma", "volume", calculate_volume_sma, {"period": 20}),
        ("rolling_vwap", "volume", calculate_rolling_vwap, {"period": 96}),
        ("force_index", "volume", calculate_force_index, {"period": 1, "smoothing_period": 13, "source": "close"}),
        ("volume_ema", "volume", calculate_volume_ema, {"period": 20}),
        ("chaikin_oscillator", "volume", calculate_chaikin_oscillator, {"fast_period": 3, "slow_period": 10}),
        ("negative_volume_index", "volume", calculate_negative_volume_index, {"initial_value": 1000.0}),
        ("positive_volume_index", "volume", calculate_positive_volume_index, {"initial_value": 1000.0}),
        ("adx", "market_strength", calculate_adx, {"period": 14}),
        ("aroon", "market_strength", calculate_aroon, {"period": 25}),
        ("vortex", "market_strength", calculate_vortex, {"period": 14}),
        ("choppiness_index", "market_strength", calculate_choppiness_index, {"period": 14}),
        ("dmi", "market_strength", calculate_dmi, {"period": 14}),
        ("elder_ray_index", "market_strength", calculate_elder_ray, {"period": 13}),
        ("plus_di", "market_strength", calculate_plus_di, {"period": 14}),
        ("minus_di", "market_strength", calculate_minus_di, {"period": 14}),
        ("pivot_points", "structure", calculate_pivot_points, {}),
        ("support_resistance", "structure", calculate_support_resistance, {"period": 20}),
        ("swing_high_low", "structure", calculate_swing_points, {"period": 5}),
        ("price_channels", "structure", calculate_price_channels, {"period": 20}),
        ("fibonacci_retracement", "structure", calculate_fibonacci_retracement, {"period": 20}),
        ("linear_regression_channel", "structure", calculate_linear_regression_channel, {"period": 20, "deviations": 2.0, "source": "close"}),
        ("breakout_detection", "structure", calculate_breakout_detection, {"period": 20}),
        ("fair_value_gap", "structure", calculate_fair_value_gap, {}),
        ("order_block", "structure", calculate_order_block, {"period": 20}),
        ("market_structure", "structure", calculate_market_structure, {"period": 20}),
        ("candlestick", "candlestick", calculate_candlestick_patterns, {}),
    ]
    for name, category, function, defaults in definitions:
        indicator_registry.register(
            name,
            category,
            function,
            defaults,
            description=f"Calculate {name.replace('_', ' ')}.",
            **_INDICATOR_METADATA[name],
        )
    indicator_registry.validate_dependencies()


_register_defaults()
INDICATOR_REGISTRY = {
    name: indicator_registry.get(name)["function"]
    for name in indicator_registry.list_names()
}


def get_indicator(name: str) -> Callable:
    return indicator_registry.get(name)["function"]


def list_indicators() -> list[str]:
    return indicator_registry.list_names()
