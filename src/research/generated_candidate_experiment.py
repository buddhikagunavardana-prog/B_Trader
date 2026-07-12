import time
from pathlib import Path

import pandas as pd

from src.research.pipeline.pipeline_executor import (
    execute_tasks,
    get_worker_market_data,
)
from src.research.pipeline.pipeline_filters import prevent_duplicate_ids
from src.research.pipeline.pipeline_loader import load_json_config, load_market_data
from src.research.pipeline.pipeline_metrics import add_research_score_columns
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report
from src.research.pipeline.pipeline_runner import build_strategy_pair_tasks
from src.research.strategy_combination_lab import MAX_WORKERS, _run_backtest_grid
from src.strategies.json_strategy_loader import load_enabled_json_strategies
from src.strategies.parameter_generator import ParameterGenerator
from src.strategies.strategy_factory import create_strategy_from_json_config


CONFIG_PATH = Path("src/config/generated_candidate_experiment.json")
SL_VALUES = [1, 1.5, 2, 2.5]
TP_VALUES = [2, 3, 4, 5]


def load_experiment_config(config_path: Path = CONFIG_PATH) -> dict:
    required_fields = [
        "enabled",
        "include_fixed_strategies",
        "generated_candidate_limit",
        "pairs",
        "timeframe",
        "lookback",
        "output_report",
    ]

    return load_json_config(config_path, required_fields)


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
    prevent_duplicate_ids(records, "strategy_id", "strategy")


def _score_report(report: pd.DataFrame) -> pd.DataFrame:
    return add_research_score_columns(report)


def _evaluate_strategy_pair(task):
    strategy_index = task.item_index
    pair_index = task.pair_index
    symbol = task.pair
    record = task.payload
    timeframe = task.timeframe
    started_at = time.perf_counter()
    df = get_worker_market_data(symbol).copy()
    results = _run_backtest_grid(
        df,
        record["strategy"],
        SL_VALUES,
        TP_VALUES,
        include_trade_details=True,
    )
    best = results.iloc[0]
    trade_records = []
    for trade in best["_Trade Records"]:
        trade_records.append({
            "Candidate ID": record["strategy_id"],
            "Strategy ID": record["strategy_id"],
            "Strategy Name": record["strategy_name"],
            "Strategy Source": record["strategy_source"],
            "Template Type": record["template_type"],
            "Pair": symbol,
            "Timeframe": timeframe,
            "Trade ID": trade["trade_id"],
            "Entry Time": trade["entry_time"],
            "Exit Time": trade["exit_time"],
            "Entry Price": trade["entry_price"],
            "Exit Price": trade["exit_price"],
            "Side": trade["direction"],
            "PnL": trade["pnl_amount"],
            "PnL %": trade["pnl_pct"],
            "Fees": trade.get("total_fee", 0.0),
            "Exit Reason": trade["exit_reason"],
            "Initial Balance": trade["balance_before"] if trade["trade_id"] == 1 else None,
        })

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
        "_trade_records": trade_records,
    }


def _build_tasks(records: list[dict], pairs: list[str], timeframe: str) -> list[tuple]:
    return build_strategy_pair_tasks(records, pairs, timeframe)


def _run_records(
    records: list[dict],
    market_data: dict,
    pairs: list[str],
    timeframe: str,
    trade_records: list[dict] | None = None,
) -> tuple[pd.DataFrame, float]:
    started_at = time.perf_counter()
    tasks = _build_tasks(records, pairs, timeframe)
    rows, failures = execute_tasks(
        tasks,
        _evaluate_strategy_pair,
        MAX_WORKERS,
        market_data=market_data,
    )

    if failures:
        for failure in failures:
            task = failure["task"]
            print(
                "Generated experiment task failed: "
                f"{task.payload['strategy_name']} | {task.pair} | "
                f"{failure['error']}"
            )

    if trade_records is not None:
        for row in rows:
            trade_records.extend(row.pop("_trade_records", []))
    else:
        for row in rows:
            row.pop("_trade_records", None)

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
    market_data = load_market_data(pairs, timeframe, lookback)

    print("\n===== B TRADER GENERATED CANDIDATE EXPERIMENT =====")
    print(f"Fixed strategy count: {len(fixed_records)}")
    print(f"Generated strategy count: {len(generated_records)}")
    print(f"Pairs: {', '.join(pairs)}")

    candidate_trades = []
    fixed_report, fixed_runtime = _run_records(
        fixed_records,
        market_data,
        pairs,
        timeframe,
        candidate_trades,
    )
    generated_report, generated_runtime = _run_records(
        generated_records,
        market_data,
        pairs,
        timeframe,
        candidate_trades,
    )

    report = pd.concat([fixed_report, generated_report], ignore_index=True)
    report = report.sort_values(
        by=["Overall Score", "Profit Factor", "ROI %"],
        ascending=False,
    )

    save_csv_report(report, config["output_report"])
    trade_output_report = config.get("trade_output_report")
    if trade_output_report:
        trade_columns = [
            "Candidate ID", "Strategy ID", "Strategy Name", "Strategy Source",
            "Template Type", "Pair", "Timeframe", "Trade ID", "Entry Time",
            "Exit Time", "Entry Price", "Exit Price", "Side", "PnL", "PnL %",
            "Fees", "Exit Reason", "Initial Balance",
        ]
        save_csv_report(
            pd.DataFrame(candidate_trades, columns=trade_columns),
            trade_output_report,
        )

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
    save_json_report(summary, summary_report)

    total_tasks = len(all_records) * len(pairs)
    _print_summary(fixed_report, generated_report, summary, total_tasks)
    print(f"\nComparison report saved -> {config['output_report']}")
    print(f"Summary report saved -> {summary_report}")

    return report, summary


if __name__ == "__main__":
    run_generated_candidate_experiment()
