from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/monte_carlo.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "simulation_count",
    "random_seed",
    "confidence_levels",
    "shuffle_trade_order",
    "sample_with_replacement",
    "slippage_enabled",
    "slippage_range_pct",
    "fee_perturbation_enabled",
    "fee_range_pct",
    "missed_trade_enabled",
    "missed_trade_probability",
    "return_noise_enabled",
    "return_noise_std_pct",
    "maximum_drawdown_limit_pct",
    "minimum_positive_run_rate",
    "maximum_ruin_probability",
    "output_report",
    "output_summary",
]


@dataclass(frozen=True)
class MonteCarloContext:
    enabled: bool
    simulation_count: int
    random_seed: int
    confidence_levels: list[float]
    shuffle_trade_order: bool
    sample_with_replacement: bool
    slippage_enabled: bool
    slippage_range_pct: list[float]
    fee_perturbation_enabled: bool
    fee_range_pct: list[float]
    missed_trade_enabled: bool
    missed_trade_probability: float
    return_noise_enabled: bool
    return_noise_std_pct: float
    maximum_drawdown_limit_pct: float
    minimum_positive_run_rate: float
    maximum_ruin_probability: float
    output_report: str | None
    output_summary: str | None
    minimum_simulation_count: int = 1
    maximum_simulation_count: int = 10000
    minimum_median_roi_pct: float = 0.0
    minimum_successful_simulation_ratio: float = 0.95
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_pipeline_context(self) -> PipelineContext:
        return PipelineContext(
            name="monte_carlo_validation",
            pairs=[],
            timeframe="simulation",
            lookback="prepared_trade_outcomes",
            output_report=self.output_report,
            max_workers=1,
            metadata={
                "simulation_count": self.simulation_count,
                "random_seed": self.random_seed,
                **self.metadata,
            },
        )


def load_monte_carlo_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def build_monte_carlo_context(
    config_override: dict | None = None,
) -> MonteCarloContext:
    config = load_monte_carlo_config()
    if config_override:
        config.update(config_override)

    return MonteCarloContext(
        enabled=bool(config["enabled"]),
        simulation_count=int(config["simulation_count"]),
        random_seed=int(config["random_seed"]),
        confidence_levels=[float(item) for item in config["confidence_levels"]],
        shuffle_trade_order=bool(config["shuffle_trade_order"]),
        sample_with_replacement=bool(config["sample_with_replacement"]),
        slippage_enabled=bool(config["slippage_enabled"]),
        slippage_range_pct=[float(item) for item in config["slippage_range_pct"]],
        fee_perturbation_enabled=bool(config["fee_perturbation_enabled"]),
        fee_range_pct=[float(item) for item in config["fee_range_pct"]],
        missed_trade_enabled=bool(config["missed_trade_enabled"]),
        missed_trade_probability=float(config["missed_trade_probability"]),
        return_noise_enabled=bool(config["return_noise_enabled"]),
        return_noise_std_pct=float(config["return_noise_std_pct"]),
        maximum_drawdown_limit_pct=float(config["maximum_drawdown_limit_pct"]),
        minimum_positive_run_rate=float(config["minimum_positive_run_rate"]),
        maximum_ruin_probability=float(config["maximum_ruin_probability"]),
        output_report=config.get("output_report"),
        output_summary=config.get("output_summary"),
        minimum_simulation_count=int(config.get("minimum_simulation_count", 1)),
        maximum_simulation_count=int(config.get("maximum_simulation_count", 10000)),
        minimum_median_roi_pct=float(config.get("minimum_median_roi_pct", 0.0)),
        minimum_successful_simulation_ratio=float(
            config.get("minimum_successful_simulation_ratio", 0.95)
        ),
        metadata=dict(config.get("metadata", {})),
    )
