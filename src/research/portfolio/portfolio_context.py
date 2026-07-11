from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/portfolio.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "allocation_method",
    "max_strategies",
    "max_pair_weight",
    "max_strategy_weight",
    "minimum_diversification",
    "maximum_drawdown_pct",
    "minimum_robustness",
    "minimum_profit_factor",
]


@dataclass(frozen=True)
class PortfolioContext:
    enabled: bool
    allocation_method: str
    max_strategies: int
    max_pair_weight: float
    max_strategy_weight: float
    minimum_diversification: int
    maximum_drawdown_pct: float
    minimum_robustness: float
    minimum_profit_factor: float
    output_report: str | None = None
    metrics_report: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_pipeline_context(self) -> PipelineContext:
        return PipelineContext(
            name="portfolio_builder",
            pairs=[],
            timeframe="portfolio",
            lookback="evaluated_candidates",
            output_report=self.output_report,
            max_workers=1,
            metadata={
                "allocation_method": self.allocation_method,
                "max_strategies": self.max_strategies,
                **self.metadata,
            },
        )


def load_portfolio_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def build_portfolio_context(config_override: dict | None = None) -> PortfolioContext:
    config = load_portfolio_config()
    if config_override:
        config.update(config_override)

    return PortfolioContext(
        enabled=bool(config["enabled"]),
        allocation_method=str(config["allocation_method"]),
        max_strategies=int(config["max_strategies"]),
        max_pair_weight=float(config["max_pair_weight"]),
        max_strategy_weight=float(config["max_strategy_weight"]),
        minimum_diversification=int(config["minimum_diversification"]),
        maximum_drawdown_pct=float(config["maximum_drawdown_pct"]),
        minimum_robustness=float(config["minimum_robustness"]),
        minimum_profit_factor=float(config["minimum_profit_factor"]),
        output_report=config.get("output_report"),
        metrics_report=config.get("metrics_report"),
        metadata=dict(config.get("metadata", {})),
    )
