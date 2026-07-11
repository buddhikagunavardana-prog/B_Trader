from pathlib import Path

import pandas as pd

from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


def build_run_summary(
    run_context,
    manifest: dict,
    reproducibility_report: dict,
) -> dict:
    result = manifest.get("metadata", {}).get("orchestrator_result", {})
    return {
        "Run ID": run_context.run_id,
        "Run Name": run_context.run_name,
        "Status": run_context.status,
        "Created At": run_context.created_at,
        "Completed At": run_context.completed_at,
        "Elapsed Seconds": result.get("elapsed_seconds", 0.0),
        "Repository Commit": run_context.repository_commit,
        "Repository Dirty": run_context.repository_dirty,
        "Config Hash": run_context.orchestrator_config_hash,
        "Enabled Stages": manifest.get("enabled_stages", []),
        "Completed Stages": result.get("completed_stages", []),
        "Failed Stages": result.get("failed_stages", []),
        "Artifact Count": len(manifest.get("artifacts", [])),
        "Task Usage": manifest.get("task_usage", 0),
        "Runtime Usage": manifest.get("runtime_usage", 0.0),
        "Reproducibility Status": reproducibility_report.get("status", "UNKNOWN"),
        "Warnings": manifest.get("warnings", []),
        "Errors": manifest.get("errors", []),
    }


def write_run_reports(
    run_context,
    manifest: dict,
    reproducibility_report: dict,
    summary_path: str | Path,
    reproducibility_path: str | Path,
    stage_summary_path: str | Path | None = None,
) -> dict:
    summary = build_run_summary(run_context, manifest, reproducibility_report)
    save_json_report(summary, str(summary_path))
    save_json_report(reproducibility_report, str(reproducibility_path))

    if stage_summary_path:
        stage_results = manifest.get("metadata", {}).get("orchestrator_result", {}).get(
            "stage_results",
            {},
        )
        rows = [
            {
                "Stage": stage,
                "Status": payload.get("status", ""),
                "Task Usage": payload.get("task_usage", 0),
                "Runtime Seconds": payload.get("runtime_seconds", 0.0),
                "Artifact Count": len(payload.get("artifacts", [])),
                "Message": payload.get("message", ""),
            }
            for stage, payload in stage_results.items()
        ]
        save_csv_report(pd.DataFrame(rows), str(stage_summary_path))

    return summary
