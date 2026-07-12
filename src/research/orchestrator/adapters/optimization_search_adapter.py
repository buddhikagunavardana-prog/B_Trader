from src.research.optimizer.optimizer_runner import run_parameter_optimizer
from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state,
    benchmark_settings,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report


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
    survivor_path = artifact_path_from_state(state, "funnel_final_survivors")
    if survivor_path:
        import pandas as pd

        survivor_ids = set(pd.read_csv(survivor_path)["Strategy ID"].astype(str))
        report = report[report["Strategy ID"].astype(str).isin(survivor_ids)].copy()
        candidates = [candidate for candidate in candidates if candidate.strategy_id in survivor_ids]
        save_csv_report(report, str(output_report))
    return stage_payload(
        stage.name,
        "Optimization search completed",
        task_usage=len(candidates),
        artifacts=[
            make_artifact(output_report, "selected_optimizer_candidates", stage.name, "CSV"),
            make_artifact(metadata_report, "optimizer_search_metadata", stage.name, "JSON"),
        ],
        metrics={
            "candidate_count": len(candidates),
            "rows": len(report),
            "funnel_filtered": bool(survivor_path),
        },
    )
