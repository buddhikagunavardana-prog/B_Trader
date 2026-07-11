from dataclasses import dataclass
from pathlib import Path

from src.strategies.parameter_generator import ParameterGenerator


PARAMETER_FAMILY_MAP = {
    "fast_ema": "EMA",
    "slow_ema": "EMA",
    "trend_ema": "EMA",
    "rsi_period": "RSI",
    "rsi_buy": "RSI",
    "rsi_sell": "RSI",
    "rsi_pullback": "RSI",
    "macd_fast": "MACD",
    "macd_slow": "MACD",
    "macd_signal": "MACD",
    "atr_period": "ATR",
    "atr_multiplier": "ATR",
    "bollinger_period": "Bollinger",
    "bollinger_std": "Bollinger",
    "supertrend_period": "SuperTrend",
    "supertrend_multiplier": "SuperTrend",
    "volume_period": "Volume",
    "volume_multiplier": "Volume",
}


@dataclass(frozen=True)
class ParameterDimension:
    name: str
    values: list
    family: str


@dataclass(frozen=True)
class TemplateParameterSpace:
    template_name: str
    template_id: str
    max_candidates: int
    dimensions: list[ParameterDimension]

    def to_parameter_set(self) -> dict:
        return {
            "template_name": self.template_name,
            "template_id": self.template_id,
            "enabled": True,
            "max_candidates": self.max_candidates,
            "parameters": {
                dimension.name: dimension.values
                for dimension in self.dimensions
            },
        }

    def families(self) -> set[str]:
        return {dimension.family for dimension in self.dimensions}


@dataclass(frozen=True)
class OptimizationSpace:
    source: str
    templates: list[TemplateParameterSpace]

    def supported_families(self) -> set[str]:
        families = set()
        for template in self.templates:
            families.update(template.families())

        return families


def parameter_family(parameter_name: str) -> str:
    return PARAMETER_FAMILY_MAP.get(parameter_name, "Risk")


def build_space_from_parameter_sets(
    parameter_sets: list[dict],
    source: str = "current",
) -> OptimizationSpace:
    templates = []

    for parameter_set in parameter_sets:
        dimensions = [
            ParameterDimension(
                name=name,
                values=list(values),
                family=parameter_family(name),
            )
            for name, values in sorted(parameter_set["parameters"].items())
        ]
        templates.append(TemplateParameterSpace(
            template_name=parameter_set["template_name"],
            template_id=parameter_set["template_id"],
            max_candidates=int(parameter_set["max_candidates"]),
            dimensions=dimensions,
        ))

    return OptimizationSpace(source=source, templates=templates)


def load_current_optimization_space(
    parameters_dir: Path | None = None,
) -> OptimizationSpace:
    generator = (
        ParameterGenerator(parameters_dir=parameters_dir)
        if parameters_dir is not None
        else ParameterGenerator()
    )
    return build_space_from_parameter_sets(
        generator.load_parameter_sets(),
        source="current",
    )
