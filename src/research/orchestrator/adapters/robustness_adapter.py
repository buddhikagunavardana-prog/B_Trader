from src.research.generated_strategy_robustness import run_generated_strategy_robustness
from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state,
    benchmark_settings,
    configured_lookback,
    configured_pairs,
    configured_timeframe,
    make_artifact,
    stage_payload,
)


def run_robustness_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    comparison_report = artifact_path_from_state(state, "generated_candidate_results")
    if not comparison_report:
        from src.research.orchestrator.adapters.adapter_result import blocked_payload
        return blocked_payload(stage.name, "Generated candidate comparison report is missing")

    output_report = context.run_directory() / "generated_strategy_robustness.csv"
    shortlist_report = context.run_directory() / "generated_strategy_shortlist.json"
    top_count = int(benchmark.get("robustness_top_candidate_count", 3))
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        top_count = min(top_count, 2)
    report, shortlist = run_generated_strategy_robustness({
        "enabled": True,
        "comparison_report": comparison_report,
        "output_report": str(output_report),
        "shortlist_report": str(shortlist_report),
        "pairs": configured_pairs(context),
        "timeframe": configured_timeframe(context),
        "lookback": configured_lookback(context),
        "top_candidate_count": top_count,
        "neighbor_limit": 2,
        "walk_forward_windows": min(int(benchmark.get("walk_forward_windows", 2)), 2),
        "global_max_validation_tasks": 50,
        "generated_candidate_limit": max(top_count * 4, 8),
    })
    return stage_payload(
        stage.name,
        "Robustness validation completed",
        task_usage=max(len(report), 1),
        artifacts=[
            make_artifact(output_report, "robustness_results", stage.name, "CSV"),
            make_artifact(shortlist_report, "robustness_shortlist", stage.name, "JSON"),
        ],
        metrics={"rows": len(report), "shortlist_count": len(shortlist)},
    )
