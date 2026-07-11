import src.research.generated_candidate_experiment as generated_candidate_experiment
from src.research.orchestrator.adapters.adapter_result import (
    benchmark_settings,
    configured_lookback,
    configured_pairs,
    configured_timeframe,
    make_artifact,
    stage_payload,
)


def run_generated_candidate_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    output_report = context.run_directory() / "generated_candidate_comparison.csv"
    summary_report = context.run_directory() / "generated_candidate_summary.json"
    limit = int(benchmark.get("generated_candidate_limit", 5))
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        limit = min(limit, 2)

    previous_workers = generated_candidate_experiment.MAX_WORKERS
    generated_candidate_experiment.MAX_WORKERS = 1
    try:
        report, summary = generated_candidate_experiment.run_generated_candidate_experiment({
        "enabled": True,
        "include_fixed_strategies": bool(benchmark.get("include_fixed_strategies", False)),
        "generated_candidate_limit": limit,
        "pairs": configured_pairs(context),
        "timeframe": configured_timeframe(context),
        "lookback": configured_lookback(context),
        "output_report": str(output_report),
        "summary_report": str(summary_report),
        })
    finally:
        generated_candidate_experiment.MAX_WORKERS = previous_workers
    artifacts = [
        make_artifact(output_report, "generated_candidate_results", stage.name, "CSV"),
        make_artifact(summary_report, "generated_candidate_summary", stage.name, "JSON"),
    ]
    return stage_payload(
        stage.name,
        "Generated candidate experiment completed",
        task_usage=max(len(report), 1),
        artifacts=artifacts,
        metrics={
            "rows": len(report),
            "generated_count": summary.get("generated_count", 0),
            "fixed_count": summary.get("fixed_count", 0),
        },
    )
