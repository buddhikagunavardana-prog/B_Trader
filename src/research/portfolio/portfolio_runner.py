import pandas as pd

from src.research.portfolio.portfolio_allocator import allocate_portfolio
from src.research.portfolio.portfolio_constraints import (
    filter_valid_candidates,
    validate_allocations,
)
from src.research.portfolio.portfolio_context import build_portfolio_context
from src.research.portfolio.portfolio_metrics import calculate_portfolio_metrics
from src.research.portfolio.portfolio_report import (
    candidates_to_report,
    save_portfolio_metrics,
    save_portfolio_report,
)


def run_portfolio_builder(
    candidates=None,
    config_override: dict | None = None,
    fixed_weights: dict[str, float] | None = None,
):
    context = build_portfolio_context(config_override)

    if not context.enabled:
        print("Portfolio builder disabled by config.")
        return pd.DataFrame(), {}

    candidates = list(candidates or [])
    valid_candidates, rejections = filter_valid_candidates(candidates, context)
    allocated_candidates = allocate_portfolio(
        valid_candidates,
        context,
        fixed_weights=fixed_weights,
    )
    allocation_result = validate_allocations(allocated_candidates, context)
    metrics = calculate_portfolio_metrics(allocated_candidates)
    metrics["allocation_valid"] = allocation_result.is_valid
    metrics["allocation_reasons"] = allocation_result.reasons
    metrics["rejected_count"] = len(rejections)
    metrics["rejections"] = rejections

    if context.output_report:
        report = save_portfolio_report(allocated_candidates, context.output_report)
    else:
        report = candidates_to_report(allocated_candidates)

    if context.metrics_report:
        save_portfolio_metrics(metrics, context.metrics_report)

    print("\n===== B TRADER PORTFOLIO BUILDER FOUNDATION =====")
    print(f"Input candidates: {len(candidates)}")
    print(f"Allocated candidates: {len(allocated_candidates)}")
    print(f"Allocation valid: {metrics['allocation_valid']}")

    return report, metrics


if __name__ == "__main__":
    run_portfolio_builder()
