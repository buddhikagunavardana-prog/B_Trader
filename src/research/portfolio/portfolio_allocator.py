from src.research.portfolio.portfolio_candidate import PortfolioCandidate
from src.research.portfolio.portfolio_context import PortfolioContext


def _normalize_weights(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total <= 0:
        return [0.0 for _ in weights]

    return [weight / total for weight in weights]


def allocate_equal_weight(
    candidates: list[PortfolioCandidate],
) -> list[PortfolioCandidate]:
    if not candidates:
        return []

    weight = 1.0 / len(candidates)
    return [candidate.with_allocation(weight) for candidate in candidates]


def allocate_fixed_weight(
    candidates: list[PortfolioCandidate],
    fixed_weights: dict[str, float] | None = None,
) -> list[PortfolioCandidate]:
    fixed_weights = fixed_weights or {}
    weights = [
        float(fixed_weights.get(candidate.candidate_id, candidate.allocation_weight))
        for candidate in candidates
    ]

    if sum(weights) <= 0:
        return allocate_equal_weight(candidates)

    normalized = _normalize_weights(weights)
    return [
        candidate.with_allocation(normalized[index])
        for index, candidate in enumerate(candidates)
    ]


def allocate_score_weight(
    candidates: list[PortfolioCandidate],
) -> list[PortfolioCandidate]:
    weights = [max(candidate.quality_score(), 0.0) for candidate in candidates]
    normalized = _normalize_weights(weights)

    return [
        candidate.with_allocation(normalized[index])
        for index, candidate in enumerate(candidates)
    ]


def allocate_portfolio(
    candidates: list[PortfolioCandidate],
    context: PortfolioContext,
    fixed_weights: dict[str, float] | None = None,
) -> list[PortfolioCandidate]:
    selected = candidates[: context.max_strategies]

    if context.allocation_method == "equal":
        return allocate_equal_weight(selected)

    if context.allocation_method == "fixed":
        return allocate_fixed_weight(selected, fixed_weights)

    if context.allocation_method == "score":
        return allocate_score_weight(selected)

    raise ValueError(f"Unknown portfolio allocation method: {context.allocation_method}")
