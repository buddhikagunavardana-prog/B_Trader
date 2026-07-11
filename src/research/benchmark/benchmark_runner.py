import pandas as pd

from src.research.benchmark.benchmark_context import build_benchmark_context
from src.research.benchmark.benchmark_preflight import BLOCKED, run_preflight_checks
from src.research.benchmark.benchmark_report import write_benchmark_reports
from src.research.benchmark.benchmark_shortlist import (
    build_final_ranking,
    load_candidate_metrics,
    write_shortlist_reports,
)
from src.research.benchmark.benchmark_summary import build_benchmark_summary
from src.research.benchmark.data_coverage_audit import run_data_coverage_audit
from src.research.run_management.run_manager import run_research_run_management


def _empty_outputs():
    ranking, shortlist, rejections = build_final_ranking([])
    return ranking, shortlist, rejections


def _candidate_metrics_from_run(run_result: dict) -> list[dict]:
    artifacts = run_result.get("manifest", {}).get("artifacts", [])
    candidates = []
    for artifact in artifacts:
        name = artifact.get("name", "")
        if name in {"final_candidate_metrics", "benchmark_candidate_metrics"}:
            candidates.extend(load_candidate_metrics(artifact.get("path", "")))
    return candidates


def run_full_benchmark(
    config_override: dict | None = None,
    run_manager=run_research_run_management,
) -> dict:
    context = build_benchmark_context(config_override)
    if not context.enabled:
        return {
            "status": "DISABLED",
            "message": "Full benchmark is disabled by config",
            "context": context.to_dict(),
        }

    coverage_report = run_data_coverage_audit(
        context.pairs,
        context.timeframes,
        output_report="reports/data_coverage_audit.csv",
    )
    preflight = run_preflight_checks(context, coverage_report)
    ranking, shortlist, rejections = _empty_outputs()
    run_result = None

    if preflight["status"] != BLOCKED:
        dry_run = context.mode == "DRY_RUN"
        run_result = run_manager(
            context.to_run_manager_override(),
            context.to_orchestrator_override(dry_run=dry_run),
        )
        candidates = _candidate_metrics_from_run(run_result)
        ranking, shortlist, rejections = build_final_ranking(
            candidates,
            context.final_shortlist_count,
            context.paper_trading_shortlist_count,
        )

    summary = build_benchmark_summary(
        context,
        preflight,
        coverage_report.to_dict(orient="records"),
        run_result,
        shortlist,
    )
    write_shortlist_reports(ranking, shortlist, rejections)
    stage_summary = None
    if run_result:
        stage_results = run_result.get("orchestrator_result", {}).get("stage_results", {})
        stage_summary = pd.DataFrame([
            {
                "Stage": stage,
                "Status": payload.get("status", ""),
                "Task Usage": payload.get("task_usage", 0),
                "Runtime Seconds": payload.get("runtime_seconds", 0.0),
                "Message": payload.get("message", ""),
            }
            for stage, payload in stage_results.items()
        ])
    write_benchmark_reports(summary, ranking, shortlist, rejections, stage_summary)

    return {
        "status": summary["status"],
        "context": context.to_dict(),
        "preflight": preflight,
        "coverage": coverage_report.to_dict(orient="records"),
        "run_result": run_result,
        "summary": summary,
        "ranking_rows": len(ranking),
        "shortlist": shortlist,
    }


def main() -> None:
    result = run_full_benchmark()
    print(
        "Full benchmark "
        f"{result['status']}: mode={result.get('context', {}).get('mode')}"
    )


if __name__ == "__main__":
    main()
