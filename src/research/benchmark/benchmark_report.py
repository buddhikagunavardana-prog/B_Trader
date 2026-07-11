import pandas as pd

from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


def write_benchmark_reports(
    summary: dict,
    ranking: pd.DataFrame,
    shortlist: dict,
    rejections: pd.DataFrame,
    stage_summary: pd.DataFrame | None = None,
) -> None:
    save_json_report(summary, "reports/final_benchmark_summary.json")
    save_csv_report(ranking, "reports/final_benchmark_ranking.csv")
    save_json_report(shortlist, "reports/final_benchmark_shortlist.json")
    save_csv_report(rejections, "reports/final_benchmark_rejections.csv")

    if stage_summary is None:
        rows = []
        for stage in summary.get("completed_stages", []):
            rows.append({"Stage": stage, "Status": "COMPLETED"})
        for stage in summary.get("failed_stages", []):
            rows.append({"Stage": stage, "Status": "FAILED"})
        for stage in summary.get("blocked_stages", []):
            rows.append({"Stage": stage, "Status": "BLOCKED"})
        stage_summary = pd.DataFrame(rows, columns=["Stage", "Status"])

    save_csv_report(stage_summary, "reports/benchmark_stage_summary.csv")
