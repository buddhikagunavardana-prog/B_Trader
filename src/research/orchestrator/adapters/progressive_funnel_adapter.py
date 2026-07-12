import pandas as pd

from src.research.orchestrator.adapters.adapter_result import (
    artifact_path_from_state, blocked_payload, make_artifact, stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report
from src.research.progressive_funnel import (
    evaluate_funnel_stage, funnel_config_hash, load_funnel_config,
)


def run_progressive_funnel_stage(context, stage, state):
    config = load_funnel_config()
    config_hash = funnel_config_hash(config)
    stage_config = next(item for item in config["stages"] if item["name"] == stage.name)
    input_name = stage.metadata["input_artifact"]
    source_path = artifact_path_from_state(state, input_name)
    trade_path = artifact_path_from_state(state, "candidate_trades")
    if not source_path or not trade_path:
        return blocked_payload(stage.name, "Candidate or trade artifact is missing")
    candidates = pd.read_csv(source_path)
    if "Funnel Status" in candidates.columns:
        candidates = candidates[candidates["Funnel Status"] == "PASS"].copy()
    report = evaluate_funnel_stage(candidates, pd.read_csv(trade_path), stage_config, config)
    output_path = context.run_directory() / f"{stage.name}_survivors.csv"
    audit_path = context.run_directory() / f"{stage.name}_audit.csv"
    survivors = report[report["Funnel Status"] == "PASS"].copy()
    save_csv_report(survivors, str(output_path))
    save_csv_report(report, str(audit_path))
    artifact_name = stage.metadata["output_artifact"]
    passed = int((report["Funnel Status"] == "PASS").sum()) if not report.empty else 0
    return stage_payload(
        stage.name, f"Progressive funnel {stage.name} completed",
        task_usage=len(report),
        artifacts=[
            make_artifact(output_path, artifact_name, stage.name, "CSV", metadata={"contract_version": "1", "funnel_config_hash": config_hash}),
            make_artifact(audit_path, f"{stage.name}_audit", stage.name, "CSV", metadata={"contract_version": "1", "funnel_config_hash": config_hash}),
        ],
        metrics={"input_count": len(candidates), "pass_count": passed, "rejected_count": len(report) - passed},
    )
