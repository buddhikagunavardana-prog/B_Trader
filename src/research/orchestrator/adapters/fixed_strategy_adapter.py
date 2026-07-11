import src.research.generated_candidate_experiment as generated_candidate_experiment
from src.research.orchestrator.adapters.adapter_result import (
    benchmark_settings,
    configured_lookback,
    configured_pairs,
    configured_timeframe,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_loader import load_market_data
from src.research.pipeline.pipeline_reporter import save_csv_report


def run_fixed_strategy_stage(context, stage, state):
    benchmark = benchmark_settings(context)
    pairs = configured_pairs(context)
    timeframe = configured_timeframe(context)
    records = generated_candidate_experiment.load_fixed_strategy_records()
    limit = int(benchmark.get("fixed_strategy_limit", len(records)))
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        limit = min(limit, 2)
    records = records[:limit]
    market_data = load_market_data(pairs, timeframe, configured_lookback(context))
    previous_workers = generated_candidate_experiment.MAX_WORKERS
    generated_candidate_experiment.MAX_WORKERS = 1
    try:
        report, runtime = generated_candidate_experiment._run_records(
            records,
            market_data,
            pairs,
            timeframe,
        )
    finally:
        generated_candidate_experiment.MAX_WORKERS = previous_workers
    output_report = context.run_directory() / "fixed_strategy_results.csv"
    save_csv_report(report, str(output_report))
    return stage_payload(
        stage.name,
        "Fixed strategy research completed",
        task_usage=max(len(records) * len(pairs), 1),
        artifacts=[make_artifact(output_report, "fixed_strategy_results", stage.name, "CSV")],
        metrics={"rows": len(report), "runtime_seconds": round(runtime, 2)},
    )
