from src.research.pipeline.pipeline_reporter import save_json_report
from src.research.orchestrator.adapters.adapter_result import make_artifact, stage_payload


def run_final_summary_stage(context, stage, state):
    output_path = context.run_directory() / "production_final_summary.json"
    payload = {
        "run_id": context.run_id,
        "completed_stages": list(state.completed_stages),
        "failed_stages": list(state.failed_stages),
        "blocked_stages": list(state.blocked_stages),
        "artifact_count": len(state.artifact_manifest),
        "paper_trading_ready": False,
        "conclusion": "Production integration summary only; no trading conclusion.",
    }
    save_json_report(payload, str(output_path))
    return stage_payload(
        stage.name,
        "Production final summary completed",
        task_usage=1,
        artifacts=[make_artifact(output_path, "final_summary", stage.name, "JSON")],
        metrics=payload,
    )
