import pandas as pd

from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state,
    blocked_payload,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report


def run_walk_forward_stage(context, stage, state):
    source_path = (
        artifact_path_from_state(state, "funnel_final_survivors")
        or artifact_path_from_state(state, "generated_candidate_results")
    )
    if not source_path:
        return blocked_payload(stage.name, "Generated candidate result artifact is missing")

    candidates = pd.read_csv(source_path).head(2)
    output_report = context.run_directory() / "walk_forward_results.csv"
    rows = []
    for _, row in candidates.iterrows():
        rows.append({
            "Strategy": row.get("Strategy Name", row.get("Strategy ID", "")),
            "Pair": row.get("Pair", ""),
            "Walk Forward Score": 0.0,
            "Status": "NOT_EVALUATED_IN_ADAPTER_SMOKE",
            "Notes": "Detailed walk-forward remains delegated to robustness engine for this integration phase.",
        })
    report = pd.DataFrame(rows)
    save_csv_report(report, str(output_report))
    return stage_payload(
        stage.name,
        "Walk-forward adapter registered candidate handoff artifact",
        task_usage=len(report),
        artifacts=[make_artifact(output_report, "walk_forward_results", stage.name, "CSV")],
        metrics={"rows": len(report)},
        warnings=["Detailed walk-forward is delegated to robustness validation in Phase 20.6"],
    )
