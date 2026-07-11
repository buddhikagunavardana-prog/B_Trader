from dataclasses import dataclass, field

from src.research.portfolio.portfolio_candidate import PortfolioCandidate
from src.research.portfolio.portfolio_context import PortfolioContext


@dataclass(frozen=True)
class PortfolioConstraintResult:
    is_valid: bool
    reasons: list[str] = field(default_factory=list)


def validate_candidate_thresholds(
    candidate: PortfolioCandidate,
    context: PortfolioContext,
) -> PortfolioConstraintResult:
    reasons = []

    if abs(candidate.drawdown) > context.maximum_drawdown_pct:
        reasons.append("drawdown above maximum threshold")

    if candidate.robustness_score < context.minimum_robustness:
        reasons.append("robustness below minimum threshold")

    if candidate.profit_factor < context.minimum_profit_factor:
        reasons.append("profit factor below minimum threshold")

    return PortfolioConstraintResult(is_valid=not reasons, reasons=reasons)


def filter_valid_candidates(
    candidates: list[PortfolioCandidate],
    context: PortfolioContext,
) -> tuple[list[PortfolioCandidate], list[dict]]:
    valid_candidates = []
    rejections = []

    for candidate in candidates:
        result = validate_candidate_thresholds(candidate, context)
        if result.is_valid:
            valid_candidates.append(candidate)
            continue

        rejections.append({
            "candidate_id": candidate.candidate_id,
            "strategy_id": candidate.strategy_id,
            "pair": candidate.pair,
            "reasons": result.reasons,
        })

    return valid_candidates, rejections


def validate_allocations(
    candidates: list[PortfolioCandidate],
    context: PortfolioContext,
) -> PortfolioConstraintResult:
    reasons = []
    total_weight = sum(candidate.allocation_weight for candidate in candidates)
    strategy_weights = {}
    pair_weights = {}

    for candidate in candidates:
        strategy_weights[candidate.strategy_id] = (
            strategy_weights.get(candidate.strategy_id, 0.0)
            + candidate.allocation_weight
        )
        pair_weights[candidate.pair] = (
            pair_weights.get(candidate.pair, 0.0)
            + candidate.allocation_weight
        )

    if total_weight > 1.000001:
        reasons.append("total allocation weight above 1.0")

    if len(strategy_weights) < context.minimum_diversification:
        reasons.append("minimum diversification not met")

    for strategy_id, weight in strategy_weights.items():
        if weight > context.max_strategy_weight + 0.000001:
            reasons.append(f"strategy allocation above maximum: {strategy_id}")

    for pair, weight in pair_weights.items():
        if weight > context.max_pair_weight + 0.000001:
            reasons.append(f"pair allocation above maximum: {pair}")

    return PortfolioConstraintResult(is_valid=not reasons, reasons=reasons)
