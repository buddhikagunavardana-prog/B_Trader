from src.research.orchestrator.adapters.best_selector_adapter import (
    run_best_selector_stage,
)
from src.research.orchestrator.adapters.final_summary_adapter import (
    run_final_summary_stage as run_production_final_summary_stage,
)
from src.research.orchestrator.adapters.fixed_strategy_adapter import (
    run_fixed_strategy_stage,
)
from src.research.orchestrator.adapters.generated_candidate_adapter import (
    run_generated_candidate_stage,
)
from src.research.orchestrator.adapters.load_data_adapter import run_load_data_stage
from src.research.orchestrator.adapters.market_regime_adapter import (
    run_market_regime_stage,
)
from src.research.orchestrator.adapters.monte_carlo_adapter import (
    run_monte_carlo_stage,
)
from src.research.orchestrator.adapters.optimization_search_adapter import (
    run_optimization_search_stage,
)
from src.research.orchestrator.adapters.parameter_optimization_adapter import (
    run_parameter_optimization_stage,
)
from src.research.orchestrator.adapters.portfolio_adapter import run_portfolio_stage
from src.research.orchestrator.adapters.robustness_adapter import (
    run_robustness_stage,
)
from src.research.orchestrator.adapters.smoke_adapter import (
    run_final_summary_stage,
    run_monte_carlo_smoke_stage,
    run_optimizer_smoke_stage,
    run_synthetic_metadata_stage,
)
from src.research.orchestrator.adapters.walk_forward_adapter import (
    run_walk_forward_stage,
)
from src.research.orchestrator.orchestrator_stage import OrchestratorStage


SMOKE = "SMOKE"
PRODUCTION = "PRODUCTION"


def _stage(
    name: str,
    display_name: str,
    dependencies: list[str] | None = None,
    runner=None,
    required: bool = True,
    output_artifacts: list[str] | None = None,
    adapter_mode: str = SMOKE,
) -> OrchestratorStage:
    return OrchestratorStage(
        name=name,
        display_name=display_name,
        dependencies=list(dependencies or []),
        runner=runner,
        required=required,
        output_artifacts=list(output_artifacts or []),
        metadata={"adapter_mode": adapter_mode},
    )


def _build_smoke_stage_registry() -> dict[str, OrchestratorStage]:
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


def _build_production_stage_registry() -> dict[str, OrchestratorStage]:
    return {
        "load_data": _stage(
            "load_data",
            "Load Historical Data",
            runner=run_load_data_stage,
            output_artifacts=["market_data_manifest", "data_coverage_audit"],
            adapter_mode=PRODUCTION,
        ),
        "fixed_strategy_research": _stage(
            "fixed_strategy_research",
            "Fixed Strategy Research",
            ["load_data"],
            runner=run_fixed_strategy_stage,
            output_artifacts=["fixed_strategy_results"],
            adapter_mode=PRODUCTION,
        ),
        "generated_candidate_research": _stage(
            "generated_candidate_research",
            "Generated Candidate Research",
            ["fixed_strategy_research"],
            runner=run_generated_candidate_stage,
            output_artifacts=["generated_candidate_results"],
            adapter_mode=PRODUCTION,
        ),
        "optimization_search": _stage(
            "optimization_search",
            "Optimization Search",
            ["generated_candidate_research"],
            runner=run_optimization_search_stage,
            output_artifacts=["selected_optimizer_candidates"],
            adapter_mode=PRODUCTION,
        ),
        "parameter_optimization": _stage(
            "parameter_optimization",
            "Parameter Optimization",
            ["optimization_search"],
            runner=run_parameter_optimization_stage,
            output_artifacts=["optimization_results"],
            adapter_mode=PRODUCTION,
        ),
        "walk_forward": _stage(
            "walk_forward",
            "Walk Forward Validation",
            ["parameter_optimization"],
            runner=run_walk_forward_stage,
            output_artifacts=["walk_forward_results"],
            adapter_mode=PRODUCTION,
        ),
        "market_regime": _stage(
            "market_regime",
            "Market Regime Detection",
            ["walk_forward"],
            runner=run_market_regime_stage,
            output_artifacts=["market_regime_results"],
            adapter_mode=PRODUCTION,
        ),
        "robustness_validation": _stage(
            "robustness_validation",
            "Robustness Validation",
            ["market_regime"],
            runner=run_robustness_stage,
            output_artifacts=["robustness_results", "robustness_shortlist"],
            adapter_mode=PRODUCTION,
        ),
        "portfolio_builder": _stage(
            "portfolio_builder",
            "Portfolio Builder",
            ["robustness_validation"],
            runner=run_portfolio_stage,
            output_artifacts=["portfolio_results", "portfolio_metrics"],
            adapter_mode=PRODUCTION,
        ),
        "monte_carlo": _stage(
            "monte_carlo",
            "Monte Carlo Validation",
            ["portfolio_builder"],
            runner=run_monte_carlo_stage,
            output_artifacts=["monte_carlo_results", "monte_carlo_summary"],
            adapter_mode=PRODUCTION,
        ),
        "best_strategy_selection": _stage(
            "best_strategy_selection",
            "Best Strategy Selection",
            ["monte_carlo"],
            runner=run_best_selector_stage,
            output_artifacts=["final_ranking", "paper_trading_shortlist"],
            adapter_mode=PRODUCTION,
        ),
        "final_summary": _stage(
            "final_summary",
            "Final Summary",
            ["best_strategy_selection"],
            runner=run_production_final_summary_stage,
            output_artifacts=["final_summary"],
            adapter_mode=PRODUCTION,
        ),
    }


def build_default_stage_registry(mode: str = SMOKE) -> dict[str, OrchestratorStage]:
    mode = str(mode or SMOKE).upper()
    if mode == PRODUCTION:
        return _build_production_stage_registry()
    if mode == SMOKE:
        return _build_smoke_stage_registry()
    raise ValueError(f"Unknown orchestrator registry mode: {mode}")


def get_stage(name: str, registry: dict[str, OrchestratorStage] | None = None):
    registry = registry or build_default_stage_registry()
    if name not in registry:
        raise ValueError(f"Unknown orchestrator stage: {name}")

    return registry[name]
