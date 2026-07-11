from src.research.optimizer.optimizer_runner import run_parameter_optimizer
from src.research.orchestrator.adapters.adapter_result import (
    benchmark_settings,
    make_artifact,
    stage_payload,
)


def run_optimization_search_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    output_report = context.run_directory() / "optimizer_candidates.csv"
    metadata_report = context.run_directory() / "optimizer_search_metadata.json"
    budget = int(benchmark.get("optimization_candidate_budget", 10))
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        budget = min(budget, 3)
    report, candidates = run_parameter_optimizer({
        "enabled": True,
        "search_algorithm": benchmark.get("optimization_search_algorithm", "grid"),
        "random_seed": int(benchmark.get("random_seed", context.random_seed)),
        "max_candidates": budget,
        "optimization_budget": budget,
        "parallel_workers": 1,
        "output_report": str(output_report),
        "search_metadata_report": str(metadata_report),
    })
    return stage_payload(
        stage.name,
        "Optimization search completed",
        task_usage=len(candidates),
        artifacts=[
            make_artifact(output_report, "selected_optimizer_candidates", stage.name, "CSV"),
            make_artifact(metadata_report, "optimizer_search_metadata", stage.name, "JSON"),
        ],
        metrics={"candidate_count": len(candidates), "rows": len(report)},
    )
