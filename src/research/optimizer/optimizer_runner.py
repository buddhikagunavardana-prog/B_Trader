import itertools

import pandas as pd

from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.optimizer.optimizer_constraints import validate_optimizer_parameters
from src.research.optimizer.optimizer_context import build_optimizer_context
from src.research.optimizer.optimizer_report import (
    candidates_to_report,
    save_candidate_report,
)
from src.research.optimizer.optimizer_space import load_current_optimization_space
from src.strategies.template_registry import StrategyTemplateRegistry


def _parameter_combinations(template_space):
    parameters = template_space.to_parameter_set()["parameters"]
    keys = sorted(parameters)
    values = [parameters[key] for key in keys]

    for combination in itertools.product(*values):
        params = dict(zip(keys, combination))
        params["template_id"] = template_space.template_id
        params["timeframe"] = "15m"
        yield params


def build_optimization_candidates(
    max_candidates: int,
    strict_constraints: bool = True,
) -> list[OptimizationCandidate]:
    registry = StrategyTemplateRegistry()
    space = load_current_optimization_space()
    candidates = []

    for template_space in space.templates:
        for parameters in _parameter_combinations(template_space):
            validation = validate_optimizer_parameters(parameters)
            if strict_constraints and not validation.is_valid:
                continue

            strategy_config = registry.build_strategy_config({
                "template_name": template_space.template_name,
                "parameters": parameters,
            })
            candidates.append(OptimizationCandidate.create(
                strategy_id=strategy_config["strategy_id"],
                template_type=template_space.template_name,
                parameters=parameters,
                validation=validation,
                optimization_metadata={
                    "space": space.source,
                    "template_id": template_space.template_id,
                },
            ))

            if len(candidates) >= max_candidates:
                return candidates

    return candidates


def run_parameter_optimizer(config_override: dict | None = None):
    context = build_optimizer_context(config_override)

    if not context.enabled:
        print("Parameter optimizer disabled by config.")
        return pd.DataFrame(), []

    candidate_limit = min(context.max_candidates, context.optimization_budget)
    candidates = build_optimization_candidates(
        max_candidates=candidate_limit,
        strict_constraints=context.strict_constraints,
    )

    if context.output_report:
        report = save_candidate_report(candidates, context.output_report)
    else:
        report = candidates_to_report(candidates)

    print("\n===== B TRADER PARAMETER OPTIMIZER FOUNDATION =====")
    print(f"Candidates prepared: {len(candidates)}")
    if context.output_report:
        print(f"Candidate report saved -> {context.output_report}")

    return report, candidates


if __name__ == "__main__":
    run_parameter_optimizer()
