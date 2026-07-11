import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.research.strategy_combination_lab import MAX_WORKERS, _run_backtest_grid
from src.strategies.json_strategy_loader import load_enabled_json_strategies
from src.strategies.parameter_generator import ParameterGenerator
from src.strategies.strategy_factory import create_strategy_from_json_config


CONFIG_PATH = Path("src/config/generated_candidate_experiment.json")
SL_VALUES = [1, 1.5, 2, 2.5]
TP_VALUES = [2, 3, 4, 5]

_WORKER_MARKET_DATA = {}


def load_experiment_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    required_fields = [
        "enabled",
        "include_fixed_strategies",
        "generated_candidate_limit",
        "pairs",
        "timeframe",
        "lookback",
        "output_report",
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing experiment config field: {field}")

    return config


def _initialize_worker(market_data):
    global _WORKER_MARKET_DATA
    _WORKER_MARKET_DATA = market_data


def _strategy_record_from_config(config: dict, source: str) -> dict:
    return {
        "strategy_id": config["strategy_id"],
        "strategy_name": config["name"],
        "strategy_source": source,
        "template_type": config.get("template", "fixed"),
        "strategy": create_strategy_from_json_config(config),
    }


def load_fixed_strategy_records() -> list[dict]:
    return [
        _strategy_record_from_config(config, "FIXED")
        for config in load_enabled_json_strategies()
    ]


def load_generated_strategy_records(limit: int) -> list[dict]:
    candidates = ParameterGenerator().generate_candidates(
        global_max_candidates=limit,
    )

    if not candidates:
        raise ValueError("No generated candidates were produced")

    return [
        _strategy_record_from_config(candidate["config"], "GENERATED")
        for candidate in candidates
    ]


def _prevent_duplicate_strategy_ids(records: list[dict]) -> None:
    seen_ids = set()

    for record in records:
        strategy_id = record["strategy_id"]

        if strategy_id in seen_ids:
            raise ValueError(f"Duplicate strategy ID in experiment: {strategy_id}")

        seen_ids.add(strategy_id)


def _score_report(report: pd.DataFrame) -> pd.DataFrame:
    scored = report.copy()
    scored["PF Score"] = scored["Profit Factor"].clip(0, 2) / 2 * 25
    scored["PnL Score"] = scored["Total PnL %"].clip(0, 50) / 50 * 25
    scored["Win Score"] = scored["Win Rate %"].clip(0, 60) / 60 * 20
    scored["DD Score"] = (
        1 - scored["Max Drawdown %"].abs().clip(0, 40) / 40
    ) * 20
    scored["Trade Score"] = scored["Trades"].clip(0, 200) / 200 * 10
    scored["Overall Score"] = (
        scored["PF Score"]
        + scored["PnL Score"]
        + scored["Win Score"]
        + scored["DD Score"]
        + scored["Trade Score"]
    )

    return scored


def _evaluate_strategy_pair(task):
    strategy_index, pair_index, symbol, record, timeframe = task
    started_at = time.perf_counter()
    df = _WORKER_MARKET_DATA[symbol].copy()
    results = _run_backtest_grid(df, record["strategy"], SL_VALUES, TP_VALUES)
    best = results.iloc[0]

    return {
        "strategy_index": strategy_index,
        "pair_index": pair_index,
        "Strategy ID": record["strategy_id"],
        "Strategy Name": record["strategy_name"],
        "Strategy Source": record["strategy_source"],
        "Template Type": record["template_type"],
        "Pair": symbol,
        "Timeframe": timeframe,
        "SL %": best["SL %"],
        "TP %": best["TP %"],
        "ROI %": best["ROI %"],
        "Profit Factor": best["Profit Factor"],
        "Total PnL %": best["Total PnL %"],
        "Win Rate %": best["Win Rate %"],
        "Max Drawdown %": best["Max Drawdown %"],
        "Trades": best["Total Trades"],
        "Expectancy": best["Expectancy"],
        "Runtime Seconds": round(time.perf_counter() - started_at, 2),
    }


def _build_tasks(records: list[dict], pairs: list[str], timeframe: str) -> list[tuple]:
    return [
        (strategy_index, pair_index, pair, record, timeframe)
        for strategy_index, record in enumerate(records)
        for pair_index, pair in enumerate(pairs)
    ]


def _run_records(
    records: list[dict],
    market_data: dict,
    pairs: list[str],
    timeframe: str,
) -> tuple[pd.DataFrame, float]:
    started_at = time.perf_counter()
    rows = []
    tasks = _build_tasks(records, pairs, timeframe)

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=_initialize_worker,
        initargs=(market_data,),
    ) as executor:
        future_map = {
            executor.submit(_evaluate_strategy_pair, task): task
            for task in tasks
        }

        for future in as_completed(future_map):
            rows.append(future.result())

    report = pd.DataFrame(rows)

    if report.empty:
        return report, time.perf_counter() - started_at

    report = _score_report(report)
    report = report.sort_values(
        by=[
            "Overall Score",
            "Profit Factor",
            "ROI %",
            "strategy_index",
            "pair_index",
        ],
        ascending=[False, False, False, True, True],
    )
    report = report.drop(columns=["strategy_index", "pair_index"])

    return report, time.perf_counter() - started_at


def _best_row(report: pd.DataFrame) -> dict:
    if report.empty:
        return {}

    return report.iloc[0].to_dict()


def _build_summary(
    fixed_report: pd.DataFrame,
    generated_report: pd.DataFrame,
    fixed_runtime: float,
    generated_runtime: float,
) -> dict:
    best_fixed = _best_row(fixed_report)
    best_generated = _best_row(generated_report)

    if best_fixed and best_generated:
        improvement = {
            "roi_pct": round(best_generated["ROI %"] - best_fixed["ROI %"], 2),
            "profit_factor": round(
                best_generated["Profit Factor"] - best_fixed["Profit Factor"],
                2,
            ),
            "win_rate_pct": round(
                best_generated["Win Rate %"] - best_fixed["Win Rate %"],
                2,
            ),
            "max_drawdown_pct": round(
                abs(best_fixed["Max Drawdown %"])
                - abs(best_generated["Max Drawdown %"]),
                2,
            ),
            "overall_score": round(
                best_generated["Overall Score"] - best_fixed["Overall Score"],
                2,
            ),
        }
    else:
        improvement = {
            "roi_pct": 0,
            "profit_factor": 0,
            "win_rate_pct": 0,
            "max_drawdown_pct": 0,
            "overall_score": 0,
        }

    return {
        "fixed_count": int(fixed_report["Strategy ID"].nunique())
        if not fixed_report.empty
        else 0,
        "generated_count": int(generated_report["Strategy ID"].nunique())
        if not generated_report.empty
        else 0,
        "fixed_runtime_seconds": round(fixed_runtime, 2),
        "generated_runtime_seconds": round(generated_runtime, 2),
        "best_fixed": best_fixed,
        "best_generated": best_generated,
        "improvement": improvement,
    }


def _print_summary(
    fixed_report: pd.DataFrame,
    generated_report: pd.DataFrame,
    summary: dict,
    total_tasks: int,
) -> None:
    print("\n===== GENERATED CANDIDATE EXPERIMENT SUMMARY =====")
    print(f"Fixed strategy count: {summary['fixed_count']}")
    print(f"Generated strategy count: {summary['generated_count']}")
    print(f"Total research tasks: {total_tasks}")
    print(f"Fixed runtime: {summary['fixed_runtime_seconds']} seconds")
    print(f"Generated runtime: {summary['generated_runtime_seconds']} seconds")

    print("\nTop 10 fixed strategies")
    print(fixed_report.head(10).to_string(index=False))

    print("\nTop 10 generated strategies")
    print(generated_report.head(10).to_string(index=False))

    print("\nBest fixed strategy")
    print(pd.Series(summary["best_fixed"]).to_string())

    print("\nBest generated strategy")
    print(pd.Series(summary["best_generated"]).to_string())

    print("\nGenerated improvement over fixed")
    print(pd.Series(summary["improvement"]).to_string())


def run_generated_candidate_experiment(config_override: dict | None = None):
    config = load_experiment_config()

    if config_override:
        config.update(config_override)

    if not config.get("enabled", False):
        print("Generated candidate experiment disabled by config.")
        return pd.DataFrame(), {}

    fixed_records = (
        load_fixed_strategy_records()
        if config.get("include_fixed_strategies", True)
        else []
    )
    generated_records = load_generated_strategy_records(
        int(config["generated_candidate_limit"])
    )
    all_records = fixed_records + generated_records
    _prevent_duplicate_strategy_ids(all_records)

    pairs = config["pairs"]
    timeframe = config["timeframe"]
    lookback = config["lookback"]
    market_data = {
        pair: get_cached_klines(pair, timeframe, lookback)
        for pair in pairs
    }

    print("\n===== B TRADER GENERATED CANDIDATE EXPERIMENT =====")
    print(f"Fixed strategy count: {len(fixed_records)}")
    print(f"Generated strategy count: {len(generated_records)}")
    print(f"Pairs: {', '.join(pairs)}")

    fixed_report, fixed_runtime = _run_records(
        fixed_records,
        market_data,
        pairs,
        timeframe,
    )
    generated_report, generated_runtime = _run_records(
        generated_records,
        market_data,
        pairs,
        timeframe,
    )

    report = pd.concat([fixed_report, generated_report], ignore_index=True)
    report = report.sort_values(
        by=["Overall Score", "Profit Factor", "ROI %"],
        ascending=False,
    )

    os.makedirs(Path(config["output_report"]).parent, exist_ok=True)
    report.to_csv(config["output_report"], index=False)

    summary = _build_summary(
        fixed_report,
        generated_report,
        fixed_runtime,
        generated_runtime,
    )
    summary_report = config.get(
        "summary_report",
        "reports/generated_candidate_summary.json",
    )
    with open(summary_report, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    total_tasks = len(all_records) * len(pairs)
    _print_summary(fixed_report, generated_report, summary, total_tasks)
    print(f"\nComparison report saved -> {config['output_report']}")
    print(f"Summary report saved -> {summary_report}")

    return report, summary


if __name__ == "__main__":
    run_generated_candidate_experiment()
