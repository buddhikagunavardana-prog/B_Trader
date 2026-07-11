import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.research.market_regime_engine import (
    detect_market_regime,
    get_recommended_strategy_family,
    load_market_regime_config,
)
from src.research.orchestrator.adapters.adapter_result import (
    configured_lookback,
    configured_pairs,
    configured_timeframe,
    make_artifact,
    stage_payload,
)
from src.research.pipeline.pipeline_reporter import save_csv_report


def run_market_regime_stage(context, stage, state):
    config = load_market_regime_config()
    rows = []
    for pair in configured_pairs(context):
        df = get_cached_klines(pair, configured_timeframe(context), configured_lookback(context))
        result = detect_market_regime(df, config)
        rows.append({
            "Pair": pair,
            "Date": pd.to_datetime(df["open_time"]).max().date().isoformat(),
            "Regime": result["regime"],
            "Confidence": result["confidence"],
            "Reasons": " | ".join(result["reasons"]),
            "Recommended Strategy Family": get_recommended_strategy_family(result["regime"]),
        })
    report = pd.DataFrame(rows)
    output_report = context.run_directory() / "market_regime_results.csv"
    save_csv_report(report, str(output_report))
    return stage_payload(
        stage.name,
        "Market regime detection completed",
        task_usage=len(rows),
        artifacts=[make_artifact(output_report, "market_regime_results", stage.name, "CSV")],
        metrics={"rows": len(rows)},
    )
