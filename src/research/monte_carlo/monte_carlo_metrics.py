import statistics

from src.research.monte_carlo.monte_carlo_context import MonteCarloContext
from src.research.monte_carlo.monte_carlo_simulator import MonteCarloSimulationResult


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    index = percentile * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = index - lower

    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    return statistics.pstdev(values)


def _bounded_score(value: float) -> float:
    return round(max(0.0, min(float(value), 100.0)), 2)


def calculate_stability_score(
    positive_run_rate: float,
    ruin_probability: float,
    roi_standard_deviation: float,
    worst_drawdown_abs: float,
) -> float:
    return _bounded_score(
        positive_run_rate * 100 * 0.35
        + (1 - ruin_probability) * 100 * 0.25
        + max(0.0, 100 - roi_standard_deviation) * 0.20
        + max(0.0, 100 - worst_drawdown_abs) * 0.20
    )


def calculate_risk_score(
    ruin_probability: float,
    worst_drawdown_abs: float,
    loss_run_rate: float,
    roi_standard_deviation: float,
) -> float:
    return _bounded_score(
        ruin_probability * 100 * 0.35
        + min(worst_drawdown_abs, 100) * 0.30
        + loss_run_rate * 100 * 0.20
        + min(roi_standard_deviation, 100) * 0.15
    )


def aggregate_monte_carlo_metrics(
    results: list[MonteCarloSimulationResult],
    context: MonteCarloContext,
) -> dict:
    successful = [result for result in results if result.success]
    failed = [result for result in results if not result.success]
    roi_values = [result.roi_pct for result in successful]
    final_balances = [result.final_balance for result in successful]
    drawdowns = [result.max_drawdown_pct for result in successful]

    simulation_count = len(results)
    successful_count = len(successful)
    positive_run_rate = (
        sum(1 for result in successful if result.positive_run) / successful_count
        if successful_count
        else 0.0
    )
    loss_run_rate = 1 - positive_run_rate if successful_count else 0.0
    ruin_probability = (
        sum(1 for result in successful if result.ruin) / successful_count
        if successful_count
        else 0.0
    )
    roi_std = _std(roi_values)
    drawdown_abs_values = [abs(value) for value in drawdowns]
    worst_drawdown_abs = max(drawdown_abs_values) if drawdown_abs_values else 0.0
    stability_score = calculate_stability_score(
        positive_run_rate,
        ruin_probability,
        roi_std,
        worst_drawdown_abs,
    )
    risk_score = calculate_risk_score(
        ruin_probability,
        worst_drawdown_abs,
        loss_run_rate,
        roi_std,
    )
    confidence_intervals = {
        str(level): round(_percentile(roi_values, level), 2)
        for level in context.confidence_levels
    }

    return {
        "simulation_count": simulation_count,
        "successful_simulations": successful_count,
        "failed_simulations": len(failed),
        "positive_run_rate": round(positive_run_rate, 4),
        "loss_run_rate": round(loss_run_rate, 4),
        "ruin_probability": round(ruin_probability, 4),
        "median_final_balance": round(statistics.median(final_balances), 2)
        if final_balances
        else 0.0,
        "mean_final_balance": round(statistics.mean(final_balances), 2)
        if final_balances
        else 0.0,
        "median_roi_pct": round(statistics.median(roi_values), 2)
        if roi_values
        else 0.0,
        "mean_roi_pct": round(statistics.mean(roi_values), 2)
        if roi_values
        else 0.0,
        "worst_roi_pct": round(min(roi_values), 2) if roi_values else 0.0,
        "best_roi_pct": round(max(roi_values), 2) if roi_values else 0.0,
        "roi_standard_deviation": round(roi_std, 2),
        "median_max_drawdown_pct": round(statistics.median(drawdowns), 2)
        if drawdowns
        else 0.0,
        "worst_max_drawdown_pct": round(min(drawdowns), 2) if drawdowns else 0.0,
        "drawdown_standard_deviation": round(_std(drawdowns), 2),
        "percentile_5_roi_pct": round(_percentile(roi_values, 0.05), 2),
        "percentile_25_roi_pct": round(_percentile(roi_values, 0.25), 2),
        "percentile_50_roi_pct": round(_percentile(roi_values, 0.50), 2),
        "percentile_75_roi_pct": round(_percentile(roi_values, 0.75), 2),
        "percentile_95_roi_pct": round(_percentile(roi_values, 0.95), 2),
        "confidence_intervals": confidence_intervals,
        "stability_score": stability_score,
        "risk_score": risk_score,
    }
