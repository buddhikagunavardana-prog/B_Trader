import csv
import json
from pathlib import Path

from src.ai.research.research_analyst import (
    load_ai_research_config,
    run_research_analysis,
)
from src.research.orchestrator.adapters.adapter_result import (
    STATUS_PARTIAL,
    benchmark_settings,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_json_report


def _write_current_run_context(context, state) -> tuple[Path, Path]:
    run_directory = context.run_directory()
    shortlist_path = run_directory / "final_benchmark_shortlist.json"
    with open(shortlist_path, "r", encoding="utf-8") as file:
        shortlist = json.load(file)
    summary_path = run_directory / "ai_deterministic_summary.json"
    benchmark = benchmark_settings(context)
    summary = {
        "run_id": context.run_id,
        "status": "COMPLETED",
        "generated_candidate_count": benchmark.get("generated_candidate_limit"),
        "promising_review_count": len(shortlist.get("promising_review", [])),
        "paper_trading_ready_count": len(shortlist.get("paper_trading_ready", [])),
        "paper_trading_readiness": (
            "PAPER_TRADING_READY"
            if shortlist.get("paper_trading_ready")
            else "NOT_READY"
        ),
        "reproducibility_status": "PARTIALLY_REPRODUCIBLE",
        "warnings": [],
    }
    save_json_report(summary, str(summary_path))
    stages_path = run_directory / "ai_deterministic_stages.csv"
    with open(stages_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["Stage", "Status", "Task Usage"],
        )
        writer.writeheader()
        for name, result in state.stage_results.items():
            writer.writerow({
                "Stage": name,
                "Status": result.get("status"),
                "Task Usage": result.get("task_usage", 0),
            })
    return summary_path, stages_path


def run_ai_research_stage(context, stage, state):
    config = load_ai_research_config()
    config.update(context.metadata.get("ai_research", {}))
    if not config["enabled"]:
        return stage_payload(
            stage.name,
            "AI research review disabled; deterministic benchmark unchanged",
            task_usage=0,
            metrics={"status": "DISABLED", "provider_called": False},
        )

    local_output = context.run_directory() / "ai_research_analysis.json"
    root_output = Path(config["output_path"])
    try:
        summary_path, stages_path = _write_current_run_context(context, state)
        input_paths = dict(config["input_report_paths"])
        input_paths.update({
            "benchmark_summary": str(summary_path),
            "benchmark_shortlist": str(
                context.run_directory() / "final_benchmark_shortlist.json"
            ),
            "benchmark_stages": str(stages_path),
        })
        analysis = run_research_analysis(
            {
                **config,
                "input_report_paths": input_paths,
                "output_path": str(local_output),
            },
            write_output=True,
        )
        save_json_report(analysis, str(root_output))
        return stage_payload(
            stage.name,
            "Advisory AI research review completed",
            task_usage=1,
            artifacts=[
                make_artifact(
                    local_output,
                    "ai_research_analysis",
                    stage.name,
                    "JSON",
                    required=False,
                    metadata={
                        "advisory_only": True,
                        "provider": analysis["provider"],
                        "model": analysis["model"],
                        "run_id": analysis["run_id"],
                    },
                )
            ],
            metrics={
                "status": "COMPLETED",
                "provider": analysis["provider"],
                "recommendation_count": len(
                    analysis["recommended_experiments"]
                ),
            },
        )
    except Exception as error:
        failure = {
            "status": "FAILED_ADVISORY",
            "run_id": context.run_id,
            "advisory_only": True,
            "deterministic_benchmark_unchanged": True,
            "error_type": type(error).__name__,
            "message": str(error),
        }
        save_json_report(failure, str(local_output))
        save_json_report(failure, str(root_output))
        return stage_payload(
            stage.name,
            "AI research review failed safely; deterministic benchmark unchanged",
            task_usage=1,
            artifacts=[make_artifact(
                local_output,
                "ai_research_analysis",
                stage.name,
                "JSON",
                required=False,
                metadata={"advisory_only": True, "status": "FAILED_ADVISORY"},
            )],
            warnings=[str(error)],
            status=STATUS_PARTIAL,
            metrics={"status": "FAILED_ADVISORY"},
        )
