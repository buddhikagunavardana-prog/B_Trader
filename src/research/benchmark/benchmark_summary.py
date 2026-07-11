from src.research.benchmark.benchmark_preflight import BLOCKED


def build_benchmark_summary(
    context,
    preflight: dict,
    coverage_rows: list[dict],
    run_result: dict | None = None,
    shortlist: dict | None = None,
) -> dict:
    run_result = run_result or {}
    shortlist = shortlist or {
        "paper_trading_ready": [],
        "promising_review": [],
        "rejected_count": 0,
    }
    orchestrator_result = run_result.get("orchestrator_result", {})
    status = preflight["status"]
    if preflight["status"] != BLOCKED and run_result:
        status = run_result.get("status", status)

    return {
        "benchmark_name": context.benchmark_name,
        "mode": context.mode,
        "status": status,
        "run_id": run_result.get("run_id"),
        "pairs": list(context.pairs),
        "timeframes": list(context.timeframes),
        "data_coverage": coverage_rows,
        "fixed_strategy_count": "deferred_to_stage",
        "generated_candidate_count": context.generated_candidate_limit,
        "optimization_candidate_budget": context.optimization_candidate_budget,
        "walk_forward_windows": context.walk_forward_windows,
        "robustness_top_candidate_count": context.robustness_top_candidate_count,
        "monte_carlo_simulations": context.monte_carlo_simulations,
        "portfolio_max_strategies": context.portfolio_max_strategies,
        "paper_trading_ready_count": len(shortlist.get("paper_trading_ready", [])),
        "promising_review_count": len(shortlist.get("promising_review", [])),
        "rejected_count": shortlist.get("rejected_count", 0),
        "task_usage": orchestrator_result.get("task_usage", 0),
        "runtime_usage": orchestrator_result.get("runtime_usage", 0.0),
        "completed_stages": orchestrator_result.get("completed_stages", []),
        "failed_stages": orchestrator_result.get("failed_stages", []),
        "blocked_stages": orchestrator_result.get("blocked_stages", []),
        "warnings": list(preflight.get("warnings", [])) + list(run_result.get("manifest", {}).get("warnings", [])),
        "failures": list(preflight.get("errors", [])) + list(run_result.get("manifest", {}).get("errors", [])),
        "reproducibility_status": run_result.get("reproducibility", {}).get("status", "NOT_RUN"),
        "paper_trading_readiness": (
            "READY"
            if shortlist.get("paper_trading_ready")
            else "NOT_READY"
        ),
        "honest_conclusion": (
            "Full benchmark blocked before execution; no trading conclusions produced."
            if preflight["status"] == BLOCKED
            else "Benchmark path executed; review shortlist and failures before Paper Trading."
        ),
    }
