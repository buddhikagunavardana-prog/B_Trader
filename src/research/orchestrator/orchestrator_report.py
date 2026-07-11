import pandas as pd

from src.research.orchestrator.orchestrator_result import OrchestratorResult
from src.research.orchestrator.orchestrator_state import OrchestratorState
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


STAGE_REPORT_COLUMNS = [
    "Stage",
    "Status",
    "Message",
    "Task Usage",
    "Runtime Seconds",
    "Artifact Count",
]


def build_stage_report(state: OrchestratorState) -> pd.DataFrame:
    rows = []

    for stage_name, result in state.stage_results.items():
        rows.append({
            "Stage": stage_name,
            "Status": result.get("status", ""),
            "Message": result.get("message", ""),
            "Task Usage": result.get("task_usage", 0),
            "Runtime Seconds": result.get("runtime_seconds", 0.0),
            "Artifact Count": len(result.get("artifacts", [])),
        })

    return pd.DataFrame(rows, columns=STAGE_REPORT_COLUMNS)


def write_stage_report(state: OrchestratorState, path: str) -> pd.DataFrame:
    report = build_stage_report(state)
    save_csv_report(report, path)
    return report


def write_summary_report(result: OrchestratorResult, path: str) -> None:
    save_json_report(result.to_dict(), path)


def write_artifact_manifest(artifacts: list[dict], path: str) -> None:
    save_json_report({"artifacts": artifacts}, path)
