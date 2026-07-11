import pandas as pd

from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state,
    blocked_payload,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report


def run_parameter_optimization_stage(context, stage, state):
    source_path = artifact_path_from_state(state, "selected_optimizer_candidates")
    if not source_path:
        return blocked_payload(stage.name, "Selected optimizer candidate artifact is missing")

    candidates = pd.read_csv(source_path)
    output_report = context.run_directory() / "parameter_optimization_results.csv"
    result = candidates.copy()
    result["Optimization Status"] = "SELECTED_FOR_EVALUATION"
    save_csv_report(result, str(output_report))
    return stage_payload(
        stage.name,
        "Parameter optimization candidate selection normalized",
        task_usage=len(result),
        artifacts=[make_artifact(output_report, "optimization_results", stage.name, "CSV")],
        metrics={"candidate_count": len(result)},
    )
