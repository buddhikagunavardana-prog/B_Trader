from src.research.portfolio.portfolio_candidate import PortfolioCandidate


def _weighted_average(candidates: list[PortfolioCandidate], getter) -> float:
    total_weight = sum(candidate.allocation_weight for candidate in candidates)
    if total_weight <= 0:
        return 0.0

    return sum(
        getter(candidate) * candidate.allocation_weight
        for candidate in candidates
    ) / total_weight


def calculate_diversification_score(candidates: list[PortfolioCandidate]) -> float:
    if not candidates:
        return 0.0

    unique_strategies = len({candidate.strategy_id for candidate in candidates})
    unique_pairs = len({candidate.pair for candidate in candidates})
    strategy_score = min(unique_strategies / len(candidates), 1.0) * 50.0
    pair_score = min(unique_pairs / len(candidates), 1.0) * 50.0

    return round(strategy_score + pair_score, 2)


def calculate_portfolio_metrics(
    candidates: list[PortfolioCandidate],
) -> dict:
    total_weight = sum(candidate.allocation_weight for candidate in candidates)
    average_roi = _weighted_average(candidates, lambda item: item.expected_roi)
    average_pf = _weighted_average(candidates, lambda item: item.profit_factor)
    average_robustness = _weighted_average(
        candidates,
        lambda item: item.robustness_score,
    )
    average_drawdown = _weighted_average(candidates, lambda item: item.drawdown)
    diversification_score = calculate_diversification_score(candidates)
    expected_portfolio_score = (
        max(average_roi, 0.0) * 0.25
        + min(average_pf / 2.0 * 100.0, 100.0) * 0.20
        + average_robustness * 0.25
        + max(0.0, 100.0 - abs(average_drawdown)) * 0.15
        + diversification_score * 0.15
    )

    return {
        "total_weight": round(total_weight, 6),
        "average_roi": round(average_roi, 2),
        "average_profit_factor": round(average_pf, 2),
        "average_robustness": round(average_robustness, 2),
        "average_drawdown": round(average_drawdown, 2),
        "diversification_score": round(diversification_score, 2),
        "expected_portfolio_score": round(expected_portfolio_score, 2),
        "candidate_count": len(candidates),
    }
