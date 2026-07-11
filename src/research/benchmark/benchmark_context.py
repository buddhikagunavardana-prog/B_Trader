from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/full_benchmark.json")
BENCHMARK_STAGE_ORDER = [
    "load_data",
    "fixed_strategy_research",
    "generated_candidate_research",
    "optimization_search",
    "parameter_optimization",
    "walk_forward",
    "market_regime",
    "robustness_validation",
    "portfolio_builder",
    "monte_carlo",
    "best_strategy_selection",
    "final_summary",
]
REQUIRED_CONFIG_KEYS = [
    "enabled",
    "mode",
    "benchmark_name",
    "random_seed",
    "resume_enabled",
    "fail_fast",
    "continue_on_stage_failure",
    "maximum_available_history",
    "target_history_years",
    "timeframes",
    "pairs",
    "future_pairs_disabled",
    "include_fixed_strategies",
    "include_generated_candidates",
    "generated_candidate_limit",
    "optimization_search_algorithm",
    "optimization_candidate_budget",
    "walk_forward_windows",
    "robustness_top_candidate_count",
    "monte_carlo_simulations",
    "portfolio_max_strategies",
    "global_task_budget",
    "global_runtime_budget_seconds",
    "output_directory",
    "final_shortlist_count",
    "paper_trading_shortlist_count",
]


@dataclass(frozen=True)
class BenchmarkContext:
    enabled: bool
    mode: str
    benchmark_name: str
    random_seed: int
    resume_enabled: bool
    fail_fast: bool
    continue_on_stage_failure: bool
    maximum_available_history: bool
    target_history_years: int
    timeframes: list[str]
    pairs: list[str]
    future_pairs_disabled: list[str]
    include_fixed_strategies: bool
    include_generated_candidates: bool
    generated_candidate_limit: int
    optimization_search_algorithm: str
    optimization_candidate_budget: int
    walk_forward_windows: int
    robustness_top_candidate_count: int
    monte_carlo_simulations: int
    portfolio_max_strategies: int
    global_task_budget: int
    global_runtime_budget_seconds: float
    output_directory: str
    final_shortlist_count: int
    paper_trading_shortlist_count: int
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "benchmark_name": self.benchmark_name,
            "run_id": self.run_id,
            "random_seed": self.random_seed,
            "resume_enabled": self.resume_enabled,
            "fail_fast": self.fail_fast,
            "continue_on_stage_failure": self.continue_on_stage_failure,
            "maximum_available_history": self.maximum_available_history,
            "target_history_years": self.target_history_years,
            "timeframes": list(self.timeframes),
            "pairs": list(self.pairs),
            "future_pairs_disabled": list(self.future_pairs_disabled),
            "include_fixed_strategies": self.include_fixed_strategies,
            "include_generated_candidates": self.include_generated_candidates,
            "generated_candidate_limit": self.generated_candidate_limit,
            "optimization_search_algorithm": self.optimization_search_algorithm,
            "optimization_candidate_budget": self.optimization_candidate_budget,
            "walk_forward_windows": self.walk_forward_windows,
            "robustness_top_candidate_count": self.robustness_top_candidate_count,
            "monte_carlo_simulations": self.monte_carlo_simulations,
            "portfolio_max_strategies": self.portfolio_max_strategies,
            "global_task_budget": self.global_task_budget,
            "global_runtime_budget_seconds": self.global_runtime_budget_seconds,
            "output_directory": self.output_directory,
            "final_shortlist_count": self.final_shortlist_count,
            "paper_trading_shortlist_count": self.paper_trading_shortlist_count,
            "metadata": dict(self.metadata),
        }

    def to_pipeline_context(self) -> PipelineContext:
        return PipelineContext(
            name="full_benchmark",
            pairs=list(self.pairs),
            timeframe=",".join(self.timeframes),
            lookback="maximum_available" if self.maximum_available_history else "configured",
            output_report="reports/final_benchmark_summary.json",
            max_workers=1,
            metadata=self.to_dict(),
        )

    def to_orchestrator_override(self, dry_run: bool = False) -> dict:
        return {
            "enabled": bool(self.enabled),
            "run_id": self.run_id,
            "random_seed": self.random_seed,
            "dry_run": dry_run,
            "resume_enabled": self.resume_enabled,
            "fail_fast": self.fail_fast,
            "continue_on_stage_failure": self.continue_on_stage_failure,
            "global_task_budget": self.global_task_budget,
            "global_runtime_budget_seconds": self.global_runtime_budget_seconds,
            "output_directory": self.output_directory,
            "smoke_mode": False,
            "enabled_stages": list(BENCHMARK_STAGE_ORDER),
            "stage_order": list(BENCHMARK_STAGE_ORDER),
            "metadata": {
                "adapter_mode": "PRODUCTION",
                "benchmark": self.to_dict(),
            },
        }

    def to_run_manager_override(self) -> dict:
        return {
            "enabled": bool(self.enabled),
            "base_output_directory": self.output_directory,
            "run_id": self.run_id,
            "run_name": self.benchmark_name,
            "resume": self.resume_enabled,
            "prevent_overwrite": True,
            "tags": ["benchmark", self.mode.lower()],
            "notes": f"{self.benchmark_name} | {self.mode}",
        }


def load_benchmark_config(config_path: Path = CONFIG_PATH) -> dict:
    return load_json_config(config_path, REQUIRED_CONFIG_KEYS)


def build_benchmark_context(config_override: dict | None = None) -> BenchmarkContext:
    config = load_benchmark_config()
    if config_override:
        config.update(config_override)

    mode = str(config.get("mode", "FULL_BENCHMARK")).upper()
    pairs = list(config["pairs"])
    timeframes = list(config["timeframes"])

    if mode == "SMALL_BENCHMARK":
        pairs = pairs[:1]
        timeframes = timeframes[:1]
        config["generated_candidate_limit"] = min(int(config["generated_candidate_limit"]), 5)
        config["optimization_candidate_budget"] = min(int(config["optimization_candidate_budget"]), 10)
        config["walk_forward_windows"] = min(int(config["walk_forward_windows"]), 2)
        config["robustness_top_candidate_count"] = min(int(config["robustness_top_candidate_count"]), 3)
        config["monte_carlo_simulations"] = min(int(config["monte_carlo_simulations"]), 20)
        config["portfolio_max_strategies"] = min(int(config["portfolio_max_strategies"]), 2)
        config["global_task_budget"] = min(int(config["global_task_budget"]), 100)

    if mode == "DRY_RUN":
        config["enabled"] = bool(config.get("enabled", True))

    return BenchmarkContext(
        enabled=bool(config["enabled"]),
        mode=mode,
        benchmark_name=str(config["benchmark_name"]),
        run_id=config.get("run_id"),
        random_seed=int(config["random_seed"]),
        resume_enabled=bool(config["resume_enabled"]),
        fail_fast=bool(config["fail_fast"]),
        continue_on_stage_failure=bool(config["continue_on_stage_failure"]),
        maximum_available_history=bool(config["maximum_available_history"]),
        target_history_years=int(config["target_history_years"]),
        timeframes=timeframes,
        pairs=pairs,
        future_pairs_disabled=list(config["future_pairs_disabled"]),
        include_fixed_strategies=bool(config["include_fixed_strategies"]),
        include_generated_candidates=bool(config["include_generated_candidates"]),
        generated_candidate_limit=int(config["generated_candidate_limit"]),
        optimization_search_algorithm=str(config["optimization_search_algorithm"]),
        optimization_candidate_budget=int(config["optimization_candidate_budget"]),
        walk_forward_windows=int(config["walk_forward_windows"]),
        robustness_top_candidate_count=int(config["robustness_top_candidate_count"]),
        monte_carlo_simulations=int(config["monte_carlo_simulations"]),
        portfolio_max_strategies=int(config["portfolio_max_strategies"]),
        global_task_budget=int(config["global_task_budget"]),
        global_runtime_budget_seconds=float(config["global_runtime_budget_seconds"]),
        output_directory=str(config["output_directory"]),
        final_shortlist_count=int(config["final_shortlist_count"]),
        paper_trading_shortlist_count=int(config["paper_trading_shortlist_count"]),
        metadata=dict(config.get("metadata", {})),
    )
