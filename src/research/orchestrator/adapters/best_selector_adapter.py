import pandas as pd

from src.research.benchmark.benchmark_shortlist import build_final_ranking, write_shortlist_reports
from src.research.orchestrator.adapters.adapter_result import (
    make_artifact,
    stage_payload,
)


def run_best_selector_stage(context, stage, state):
    ranking_path = context.run_directory() / "final_benchmark_ranking.csv"
    shortlist_path = context.run_directory() / "final_benchmark_shortlist.json"
    rejections_path = context.run_directory() / "final_benchmark_rejections.csv"
    ranking, shortlist, rejections = build_final_ranking([])
    write_shortlist_reports(
        ranking,
        shortlist,
        rejections,
        str(ranking_path),
        str(shortlist_path),
        str(rejections_path),
    )
    return stage_payload(
        stage.name,
        "Best selector completed with empty shortlist",
        task_usage=1,
        artifacts=[
            make_artifact(ranking_path, "final_ranking", stage.name, "CSV"),
            make_artifact(shortlist_path, "paper_trading_shortlist", stage.name, "JSON"),
            make_artifact(rejections_path, "final_rejections", stage.name, "CSV", required=False),
        ],
        metrics={"ranking_rows": len(ranking), "paper_ready_count": 0},
        warnings=["No final candidate metrics artifact available; empty shortlist produced"],
    )
