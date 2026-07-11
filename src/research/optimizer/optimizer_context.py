from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/optimizer.json")
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "search_algorithm",
    "random_seed",
    "max_candidates",
    "optimization_budget",
    "max_random_attempts",
    "resume_enabled",
    "parameter_space",
    "parallel_workers",
    "strict_constraints",
]


@dataclass(frozen=True)
class OptimizerContext:
    enabled: bool
    search_algorithm: str
    random_seed: int
    max_candidates: int
    optimization_budget: int
    max_random_attempts: int
    resume_enabled: bool
    parameter_space: str
    parallel_workers: int
    strict_constraints: bool
    pairs: list[str] = field(default_factory=list)
    timeframe: str = "15m"
    lookback: str = "synthetic"
    output_report: str | None = None
    search_metadata_report: str | None = None
    early_stopping: dict[str, Any] = field(default_factory=dict)
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
                "search_algorithm": self.search_algorithm,
                "random_seed": self.random_seed,
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
        search_algorithm=str(config["search_algorithm"]),
        random_seed=int(config["random_seed"]),
        max_candidates=int(config["max_candidates"]),
        optimization_budget=int(config["optimization_budget"]),
        max_random_attempts=int(config["max_random_attempts"]),
        resume_enabled=bool(config["resume_enabled"]),
        parameter_space=str(config["parameter_space"]),
        parallel_workers=int(config["parallel_workers"]),
        strict_constraints=bool(config["strict_constraints"]),
        pairs=list(config.get("pairs", [])),
        timeframe=str(config.get("timeframe", "15m")),
        lookback=str(config.get("lookback", "synthetic")),
        output_report=config.get("output_report"),
        search_metadata_report=config.get("search_metadata_report"),
        early_stopping=dict(config.get("early_stopping", {})),
        metadata=dict(config.get("metadata", {})),
    )
