import json

from src.research.portfolio.portfolio_candidate import PortfolioCandidate
from src.research.portfolio.portfolio_runner import run_portfolio_builder
from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state,
    benchmark_settings,
    make_artifact,
    stage_payload,
)


def _candidate_from_shortlist(item: dict) -> PortfolioCandidate:
    metrics = item.get("minimum_expected_metrics", {})
    return PortfolioCandidate.create(
        strategy_id=item["strategy_id"],
        pair=(item.get("recommended_pairs") or ["BTCUSDT"])[0],
        template_type=item.get("template_type", "generated"),
        expected_roi=float(metrics.get("roi_pct", 0.0)),
        profit_factor=float(metrics.get("profit_factor", 0.0)),
        drawdown=float(metrics.get("max_drawdown_pct", 100.0)),
        walk_forward_score=float(item.get("walk_forward_score", 0.0)),
        robustness_score=float(item.get("robustness_score", 0.0)),
        risk_score=float(item.get("overfitting_risk_score", 100.0)),
        metadata={
            "source": "robustness_shortlist",
            "name": item.get("name", item["strategy_id"]),
            "recommended_regimes": list(item.get("recommended_regimes", [])),
            "trades": int(metrics.get("trades", 0)),
        },
    )


def run_portfolio_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    shortlist_path = artifact_path_from_state(state, "robustness_shortlist")
    candidates = []
    if shortlist_path:
        with open(shortlist_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        candidates = [_candidate_from_shortlist(item) for item in payload]

    output_report = context.run_directory() / "portfolio_results.csv"
    metrics_report = context.run_directory() / "portfolio_metrics.json"
    report, metrics = run_portfolio_builder(
        candidates,
        {
            "enabled": True,
            "max_strategies": min(int(benchmark.get("portfolio_max_strategies", 2)), 2)
            if benchmark.get("mode") == "SMALL_BENCHMARK"
            else int(benchmark.get("portfolio_max_strategies", 10)),
            "output_report": str(output_report),
            "metrics_report": str(metrics_report),
        },
    )
    return stage_payload(
        stage.name,
        "Portfolio builder completed",
        task_usage=max(len(candidates), 1),
        artifacts=[
            make_artifact(output_report, "portfolio_results", stage.name, "CSV", required=False),
            make_artifact(metrics_report, "portfolio_metrics", stage.name, "JSON"),
        ],
        metrics={"input_candidates": len(candidates), "allocated_rows": len(report), **metrics},
        warnings=[] if candidates else ["No robustness shortlist candidates available for portfolio"],
    )
