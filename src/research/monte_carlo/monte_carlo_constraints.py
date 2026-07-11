from dataclasses import dataclass, field

from src.research.monte_carlo.monte_carlo_context import MonteCarloContext


@dataclass(frozen=True)
class MonteCarloConstraintResult:
    passed: bool
    status: str
    reasons: list[str] = field(default_factory=list)


def validate_constraint_config(context: MonteCarloContext) -> None:
    if context.minimum_simulation_count <= 0:
        raise ValueError("minimum_simulation_count must be positive")

    if context.maximum_simulation_count < context.minimum_simulation_count:
        raise ValueError("maximum_simulation_count cannot be lower than minimum")

    if context.maximum_ruin_probability < 0 or context.maximum_ruin_probability > 1:
        raise ValueError("maximum_ruin_probability must be between 0 and 1")

    if context.minimum_positive_run_rate < 0 or context.minimum_positive_run_rate > 1:
        raise ValueError("minimum_positive_run_rate must be between 0 and 1")

    if (
        context.minimum_successful_simulation_ratio < 0
        or context.minimum_successful_simulation_ratio > 1
    ):
        raise ValueError(
            "minimum_successful_simulation_ratio must be between 0 and 1"
        )


def evaluate_monte_carlo_constraints(
    metrics: dict,
    context: MonteCarloContext,
) -> MonteCarloConstraintResult:
    validate_constraint_config(context)
    reasons = []

    simulation_count = int(metrics["simulation_count"])
    if simulation_count < context.minimum_simulation_count:
        reasons.append("simulation count below minimum")

    if simulation_count > context.maximum_simulation_count:
        reasons.append("simulation count above maximum")

    if metrics["ruin_probability"] > context.maximum_ruin_probability:
        reasons.append("ruin probability above maximum")

    if metrics["positive_run_rate"] < context.minimum_positive_run_rate:
        reasons.append("positive run rate below minimum")

    if abs(metrics["worst_max_drawdown_pct"]) > context.maximum_drawdown_limit_pct:
        reasons.append("worst drawdown above maximum")

    if metrics["median_roi_pct"] < context.minimum_median_roi_pct:
        reasons.append("median ROI below minimum")

    successful_ratio = (
        metrics["successful_simulations"] / simulation_count
        if simulation_count
        else 0.0
    )
    if successful_ratio < context.minimum_successful_simulation_ratio:
        reasons.append("successful simulation ratio below minimum")

    return MonteCarloConstraintResult(
        passed=not reasons,
        status="PASS" if not reasons else "FAIL",
        reasons=reasons,
    )
