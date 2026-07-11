from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/optimizer.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "max_candidates",
    "optimization_budget",
    "parameter_space",
    "parallel_workers",
    "strict_constraints",
]


@dataclass(frozen=True)
class OptimizerContext:
    enabled: bool
    max_candidates: int
    optimization_budget: int
    parameter_space: str
    parallel_workers: int
    strict_constraints: bool
    pairs: list[str] = field(default_factory=list)
    timeframe: str = "15m"
    lookback: str = "synthetic"
    output_report: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_pipeline_context(self) -> PipelineContext:
        return PipelineContext(
            name="parameter_optimizer",
            pairs=self.pairs,
            timeframe=self.timeframe,
            lookback=self.lookback,
            output_report=self.output_report,
            max_workers=self.parallel_workers,
            metadata={
                "parameter_space": self.parameter_space,
                "optimization_budget": self.optimization_budget,
                **self.metadata,
            },
        )


def load_optimizer_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def build_optimizer_context(config_override: dict | None = None) -> OptimizerContext:
    config = load_optimizer_config()
    if config_override:
        config.update(config_override)

    return OptimizerContext(
        enabled=bool(config["enabled"]),
        max_candidates=int(config["max_candidates"]),
        optimization_budget=int(config["optimization_budget"]),
        parameter_space=str(config["parameter_space"]),
        parallel_workers=int(config["parallel_workers"]),
        strict_constraints=bool(config["strict_constraints"]),
        pairs=list(config.get("pairs", [])),
        timeframe=str(config.get("timeframe", "15m")),
        lookback=str(config.get("lookback", "synthetic")),
        output_report=config.get("output_report"),
        metadata=dict(config.get("metadata", {})),
    )
