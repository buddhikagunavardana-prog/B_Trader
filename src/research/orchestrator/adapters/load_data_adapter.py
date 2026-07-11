from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.research.benchmark.data_coverage_audit import run_data_coverage_audit
from src.research.orchestrator.adapters.adapter_result import (
    configured_lookback,
    configured_pairs,
    configured_timeframe,
    make_artifact,
    stage_payload,
)


REQUIRED_OHLCV_COLUMNS = {"open_time", "open", "high", "low", "close", "volume"}


def _validate_ohlcv(df: pd.DataFrame) -> None:
    missing = REQUIRED_OHLCV_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV schema missing columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("OHLCV data is empty")


def run_load_data_stage(context, stage, state):
    pairs = configured_pairs(context)
    timeframe = configured_timeframe(context)
    lookback = configured_lookback(context)
    manifest_rows = []

    for pair in pairs:
        df = get_cached_klines(pair, timeframe, lookback)
        _validate_ohlcv(df)
        manifest_rows.append({
            "pair": pair,
            "timeframe": timeframe,
            "lookback": lookback,
            "rows": len(df),
            "start": str(pd.to_datetime(df["open_time"]).min()),
            "end": str(pd.to_datetime(df["open_time"]).max()),
        })

    manifest_path = context.run_directory() / "market_data_manifest.json"
    coverage_path = context.run_directory() / "data_coverage_audit.csv"
    from src.research.pipeline.pipeline_reporter import save_json_report

    save_json_report({"market_data": manifest_rows}, str(manifest_path))
    run_data_coverage_audit(pairs, [timeframe], str(coverage_path))
    artifacts = [
        make_artifact(manifest_path, "market_data_manifest", stage.name, "JSON"),
        make_artifact(coverage_path, "data_coverage_audit", stage.name, "CSV"),
    ]
    return stage_payload(
        stage.name,
        "Loaded and validated cached market data",
        task_usage=len(pairs),
        artifacts=artifacts,
        metrics={"pair_count": len(pairs), "timeframe": timeframe},
    )
