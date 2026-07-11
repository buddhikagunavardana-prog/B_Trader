from src.research.orchestrator.adapters.smoke_adapter import (
    run_final_summary_stage,
    run_monte_carlo_smoke_stage,
    run_optimizer_smoke_stage,
    run_synthetic_metadata_stage,
)
from src.research.orchestrator.orchestrator_stage import OrchestratorStage


def _stage(
    name: str,
    display_name: str,
    dependencies: list[str] | None = None,
    runner=None,
    required: bool = True,
    output_artifacts: list[str] | None = None,
) -> OrchestratorStage:
    return OrchestratorStage(
        name=name,
        display_name=display_name,
        dependencies=list(dependencies or []),
        runner=runner,
        required=required,
        output_artifacts=list(output_artifacts or []),
    )


def build_default_stage_registry() -> dict[str, OrchestratorStage]:
    return {
        "load_data": _stage(
            "load_data",
            "Load Historical Data",
            runner=run_synthetic_metadata_stage,
            output_artifacts=["load_data.json"],
        ),
        "fixed_strategy_research": _stage(
            "fixed_strategy_research",
            "Fixed Strategy Research",
            ["load_data"],
            runner=run_synthetic_metadata_stage,
        ),
        "generated_candidate_research": _stage(
            "generated_candidate_research",
            "Generated Candidate Research",
            ["load_data"],
            runner=run_synthetic_metadata_stage,
        ),
        "optimization_search": _stage(
            "optimization_search",
            "Optimization Search",
            ["load_data"],
            runner=run_optimizer_smoke_stage,
            output_artifacts=[
                "optimizer_candidates.csv",
                "optimizer_search_metadata.json",
            ],
        ),
        "parameter_optimization": _stage(
            "parameter_optimization",
            "Parameter Optimization",
            ["optimization_search"],
            runner=run_synthetic_metadata_stage,
        ),
        "walk_forward": _stage(
            "walk_forward",
            "Walk Forward Validation",
            ["parameter_optimization"],
            runner=run_synthetic_metadata_stage,
        ),
        "market_regime": _stage(
            "market_regime",
            "Market Regime Detection",
            ["walk_forward"],
            runner=run_synthetic_metadata_stage,
        ),
        "robustness_validation": _stage(
            "robustness_validation",
            "Robustness Validation",
            ["market_regime"],
            runner=run_synthetic_metadata_stage,
        ),
        "portfolio_builder": _stage(
            "portfolio_builder",
            "Portfolio Builder",
            ["robustness_validation"],
            runner=run_synthetic_metadata_stage,
        ),
        "monte_carlo": _stage(
            "monte_carlo",
            "Monte Carlo Validation",
            ["optimization_search"],
            runner=run_monte_carlo_smoke_stage,
            output_artifacts=[
                "monte_carlo_results.csv",
                "monte_carlo_summary.json",
            ],
        ),
        "best_strategy_selection": _stage(
            "best_strategy_selection",
            "Best Strategy Selection",
            ["monte_carlo"],
            runner=run_synthetic_metadata_stage,
        ),
        "final_summary": _stage(
            "final_summary",
            "Final Summary",
            ["monte_carlo"],
            runner=run_final_summary_stage,
            output_artifacts=["final_summary.json"],
        ),
    }


def get_stage(name: str, registry: dict[str, OrchestratorStage] | None = None):
    registry = registry or build_default_stage_registry()
    if name not in registry:
        raise ValueError(f"Unknown orchestrator stage: {name}")

    return registry[name]
