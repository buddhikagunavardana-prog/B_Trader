import copy
import json
from pathlib import Path

import pandas as pd

from src.research.generated_candidate_experiment import (
    _score_report,
    load_experiment_config,
)
from src.research.market_regime_engine import (
    detect_historical_market_regimes,
    detect_market_regime,
    load_market_regime_config,
)
from src.research.pipeline.pipeline_filters import limit_by_task_budget
from src.research.pipeline.pipeline_loader import (
    load_csv_report,
    load_json_config,
    load_market_data,
)
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report
from src.research.strategy_combination_lab import _run_backtest_grid
from src.research.walk_forward_engine import (
    build_walk_forward_windows,
    calculate_walk_forward_score,
    load_walk_forward_config,
)
from src.strategies.parameter_generator import ParameterGenerator
from src.strategies.strategy_factory import create_strategy_from_json_config
from src.strategies.template_registry import StrategyTemplateRegistry


CONFIG_PATH = Path("src/config/generated_strategy_robustness.json")
REPORT_COLUMNS = [
    "Strategy ID",
    "Strategy Name",
    "Template Type",
    "Original Pair",
    "Original ROI %",
    "Original Profit Factor",
    "Original Win Rate %",
    "Original Max Drawdown %",
    "Original Trades",
    "Original Expectancy",
    "Walk Forward Pass Rate %",
    "Average Walk Forward Score",
    "Pair Consistency Score",
    "Regime Consistency Score",
    "Profitable Regime Count",
    "Observed Regime Count",
    "Regime Attribution Method",
    "Parameter Sensitivity Score",
    "Overfitting Risk Score",
    "Robustness Score",
    "Status",
    "Rejection Reasons",
]

ROBUSTNESS_WEIGHTS = {
    "walk_forward": 25,
    "pair_consistency": 20,
    "regime_consistency": 15,
    "parameter_sensitivity": 15,
    "profit_factor": 10,
    "drawdown": 10,
    "trade_count": 5,
}


def load_robustness_config(config_path: Path = CONFIG_PATH) -> dict:
    required_keys = [
        "enabled",
        "top_candidate_count",
        "neighbor_limit",
        "walk_forward_windows",
        "global_max_validation_tasks",
        "comparison_report",
        "trade_report",
        "output_report",
        "shortlist_report",
        "pairs",
        "timeframe",
        "lookback",
        "minimum_trades",
        "minimum_profit_factor",
        "maximum_drawdown_pct",
        "historical_regime_attribution_enabled",
        "historical_regime_minimum_trades",
        "maximum_neighbor_degradation_pct",
        "pass_score",
    ]

    return load_json_config(config_path, required_keys)


def _bounded_score(value: float) -> float:
    return round(max(0.0, min(float(value), 100.0)), 2)


def _load_comparison_report(path: str) -> pd.DataFrame:
    required_columns = {
        "Strategy ID",
        "Strategy Name",
        "Strategy Source",
        "Template Type",
        "Pair",
        "SL %",
        "TP %",
        "ROI %",
        "Profit Factor",
        "Win Rate %",
        "Max Drawdown %",
        "Trades",
        "Overall Score",
    }
    return load_csv_report(path, required_columns)


def _load_trade_report(path: str) -> pd.DataFrame:
    required_columns = {
        "Strategy ID",
        "Pair",
        "Entry Time",
        "PnL",
        "Initial Balance",
    }
    report = load_csv_report(path, required_columns)
    report["Entry Time"] = pd.to_datetime(
        report["Entry Time"],
        utc=True,
        errors="coerce",
    )
    report["PnL"] = pd.to_numeric(report["PnL"], errors="coerce")
    if report["Entry Time"].isna().any() or report["PnL"].isna().any():
        raise ValueError("Trade report contains invalid historical regime inputs")
    return report


def select_top_generated_candidates(
    report: pd.DataFrame,
    top_candidate_count: int,
    pairs: list[str] | None = None,
) -> pd.DataFrame:
    generated = report[report["Strategy Source"] == "GENERATED"].copy()
    if pairs:
        generated = generated[generated["Pair"].isin(pairs)].copy()

    if generated.empty:
        return generated

    generated = generated.sort_values(
        by=["Overall Score", "Profit Factor", "ROI %"],
        ascending=False,
    )

    return generated.drop_duplicates("Strategy ID").head(top_candidate_count)


def _candidate_lookup(
    limit: int,
    atr_exit_variants: dict | None = None,
) -> dict:
    candidates = ParameterGenerator().generate_candidates(
        global_max_candidates=limit,
        atr_exit_variants=atr_exit_variants,
    )
    return {
        candidate["strategy_id"]: candidate
        for candidate in candidates
    }


def _build_strategy_record(candidate: dict, top_row: pd.Series) -> dict:
    config = candidate["config"]
    return {
        "strategy_id": config["strategy_id"],
        "strategy_name": config["name"],
        "template_type": candidate["template_name"],
        "parameters": candidate["parameters"],
        "config": config,
        "strategy": create_strategy_from_json_config(config),
        "original_pair": top_row["Pair"],
        "original_sl": float(top_row["SL %"]),
        "original_tp": float(top_row["TP %"]),
    }


def resolve_top_candidate_records(
    top_candidates: pd.DataFrame,
    generator_limit: int,
    atr_exit_variants: dict | None = None,
) -> list[dict]:
    lookup = _candidate_lookup(generator_limit, atr_exit_variants)
    records = []

    for _, row in top_candidates.iterrows():
        strategy_id = row["Strategy ID"]
        if strategy_id not in lookup:
            continue

        records.append(_build_strategy_record(lookup[strategy_id], row))

    return records


def _estimate_validation_tasks(config: dict) -> int:
    return (
        int(config["walk_forward_windows"]) * 2
        + int(config["neighbor_limit"])
        + 2
    )


def _apply_validation_task_cap(records: list[dict], config: dict) -> list[dict]:
    task_estimate = _estimate_validation_tasks(config)
    return limit_by_task_budget(
        records,
        int(config["global_max_validation_tasks"]),
        task_estimate,
    )


def _metric_pass(row, config: dict) -> bool:
    return (
        float(row["Profit Factor"]) >= config["minimum_profit_factor"]
        and int(row["Trades"]) >= config["minimum_trades"]
        and abs(float(row["Max Drawdown %"])) <= config["maximum_drawdown_pct"]
    )


def calculate_pair_consistency(
    strategy_rows: pd.DataFrame,
    config: dict,
) -> dict:
    if strategy_rows.empty:
        return {
            "score": 0.0,
            "recommended_pairs": [],
            "pass_rate": 0.0,
            "worst_roi": 0.0,
        }

    passed = strategy_rows.apply(lambda row: _metric_pass(row, config), axis=1)
    pass_rate = passed.mean() * 100
    profitable_rate = (strategy_rows["ROI %"] > 0).mean() * 100
    median_roi_score = _bounded_score(strategy_rows["ROI %"].median())
    score = _bounded_score(
        pass_rate * 0.60
        + profitable_rate * 0.25
        + median_roi_score * 0.15
    )

    return {
        "score": score,
        "recommended_pairs": strategy_rows.loc[passed, "Pair"].tolist(),
        "pass_rate": round(pass_rate, 2),
        "worst_roi": round(float(strategy_rows["ROI %"].min()), 2),
    }


def _build_regime_map(market_data: dict) -> dict:
    regime_config = load_market_regime_config()
    regime_map = {}

    for pair, df in market_data.items():
        try:
            regime_map[pair] = detect_market_regime(df, regime_config)["regime"]
        except Exception as error:
            regime_map[pair] = f"UNKNOWN: {error}"

    return regime_map


def calculate_regime_consistency(
    strategy_rows: pd.DataFrame,
    regime_map: dict,
    config: dict,
) -> dict:
    if strategy_rows.empty:
        return {
            "score": 0.0,
            "recommended_regimes": [],
            "regime_count": 0,
            "observed_regime_count": 0,
            "method": "LATEST_PAIR_SNAPSHOT",
            "details": [],
        }

    regime_rows = strategy_rows.copy()
    regime_rows["Regime"] = regime_rows["Pair"].map(regime_map).fillna("UNKNOWN")
    passed = regime_rows.apply(lambda row: _metric_pass(row, config), axis=1)
    grouped = regime_rows.assign(Passed=passed).groupby("Regime")

    passed_regimes = []
    regime_scores = []
    for regime, group in grouped:
        pass_rate = group["Passed"].mean() * 100
        roi_score = _bounded_score(group["ROI %"].median())
        regime_score = _bounded_score(pass_rate * 0.75 + roi_score * 0.25)
        regime_scores.append(regime_score)

        if pass_rate >= 50:
            passed_regimes.append(regime)

    score = _bounded_score(sum(regime_scores) / len(regime_scores))

    return {
        "score": score,
        "recommended_regimes": passed_regimes,
        "regime_count": len(regime_scores),
        "observed_regime_count": len(regime_scores),
        "method": "LATEST_PAIR_SNAPSHOT",
        "details": [],
    }


def _historical_max_drawdown_pct(
    pnl_values: pd.Series,
    initial_balance: float,
) -> float:
    equity = initial_balance + pnl_values.cumsum()
    equity = pd.concat([
        pd.Series([initial_balance], dtype=float),
        equity.reset_index(drop=True),
    ], ignore_index=True)
    peaks = equity.cummax()
    drawdowns = (equity - peaks) / peaks * 100
    return float(drawdowns.min())


def calculate_historical_regime_consistency(
    candidate_trades: pd.DataFrame,
    regime_history: pd.DataFrame,
    config: dict,
) -> dict:
    if candidate_trades.empty or regime_history.empty:
        return {
            "score": 0.0,
            "recommended_regimes": [],
            "regime_count": 0,
            "observed_regime_count": 0,
            "method": "HISTORICAL_PRIOR_CANDLE",
            "details": [],
        }

    initial_values = pd.to_numeric(
        candidate_trades["Initial Balance"],
        errors="coerce",
    ).dropna()
    if initial_values.empty:
        raise ValueError("Candidate trades are missing an initial balance")
    initial_balance = float(initial_values.iloc[0])

    attributed = candidate_trades.copy()
    attributed["Entry Time"] = pd.to_datetime(
        attributed["Entry Time"],
        utc=True,
    )
    attributed = attributed.merge(
        regime_history[["open_time", "Regime"]],
        left_on="Entry Time",
        right_on="open_time",
        how="left",
        validate="many_to_one",
    ).dropna(subset=["Regime"])

    minimum_trades = int(config["historical_regime_minimum_trades"])
    recommended_regimes = []
    regime_scores = []
    regime_details = []
    observed_regimes = 0
    for regime, group in attributed.groupby("Regime"):
        observed_regimes += 1
        group = group.sort_values("Entry Time")
        trade_count = len(group)
        gross_profit = float(group.loc[group["PnL"] > 0, "PnL"].sum())
        gross_loss = abs(float(group.loc[group["PnL"] < 0, "PnL"].sum()))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        max_drawdown = _historical_max_drawdown_pct(
            group["PnL"],
            initial_balance,
        )
        roi_pct = float(group["PnL"].sum()) / initial_balance * 100
        if trade_count < minimum_trades:
            regime_details.append({
                "regime": str(regime),
                "trades": trade_count,
                "profit_factor": round(profit_factor, 2),
                "roi_pct": round(roi_pct, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "sample_sufficient": False,
                "passed": False,
            })
            continue

        metrics = pd.Series({
            "Profit Factor": profit_factor,
            "Trades": trade_count,
            "Max Drawdown %": max_drawdown,
        })
        regime_config = {
            **config,
            "minimum_trades": minimum_trades,
        }
        passed = _metric_pass(metrics, regime_config)
        regime_details.append({
            "regime": str(regime),
            "trades": trade_count,
            "profit_factor": round(profit_factor, 2),
            "roi_pct": round(roi_pct, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "sample_sufficient": True,
            "passed": bool(passed),
        })
        regime_scores.append(_bounded_score(
            (75.0 if passed else 0.0) + _bounded_score(roi_pct) * 0.25
        ))
        if passed:
            recommended_regimes.append(str(regime))

    score = (
        _bounded_score(sum(regime_scores) / len(regime_scores))
        if regime_scores else 0.0
    )
    return {
        "score": score,
        "recommended_regimes": recommended_regimes,
        "regime_count": len(regime_scores),
        "observed_regime_count": observed_regimes,
        "method": "HISTORICAL_PRIOR_CANDLE",
        "details": regime_details,
    }


def _is_valid_neighbor(parameters: dict) -> bool:
    fast_ema = parameters.get("fast_ema")
    slow_ema = parameters.get("slow_ema")

    if fast_ema is not None and slow_ema is not None:
        return int(fast_ema) < int(slow_ema)

    return True


def _neighbor_values(value, deltas: list[float]) -> list:
    values = []
    for delta in deltas:
        new_value = value + delta
        if isinstance(value, int):
            new_value = int(round(new_value))
        else:
            new_value = round(float(new_value), 2)

        if new_value > 0 and new_value != value:
            values.append(new_value)

    return values


def generate_neighbor_parameters(
    parameters: dict,
    limit: int,
) -> list[dict]:
    neighbor_specs = {
        "fast_ema": [-10, 10],
        "slow_ema": [-25, 25],
        "rsi_period": [-2, 2],
        "rsi_buy": [-5, 5],
        "rsi_pullback": [-5, 5],
        "volume_multiplier": [-0.1, 0.1],
        "atr_multiplier": [-0.25, 0.25],
        "bollinger_std": [-0.25, 0.25],
        "stop_loss_pct": [-0.5, 0.5],
        "take_profit_pct": [-1.0, 1.0],
    }
    neighbors = []
    seen = set()

    for key, deltas in neighbor_specs.items():
        if key not in parameters:
            continue

        for value in _neighbor_values(parameters[key], deltas):
            neighbor = copy.deepcopy(parameters)
            neighbor[key] = value

            if not _is_valid_neighbor(neighbor):
                continue

            signature = json.dumps(neighbor, sort_keys=True)
            if signature in seen:
                continue

            seen.add(signature)
            neighbors.append(neighbor)

            if len(neighbors) >= limit:
                return neighbors

    return neighbors


def _score_single_backtest(
    df: pd.DataFrame,
    strategy,
    sl: float,
    tp: float,
) -> pd.Series:
    results = _run_backtest_grid(df, strategy, [sl], [tp])
    return results.iloc[0]


def calculate_walk_forward_validation(
    record: dict,
    df: pd.DataFrame,
    config: dict,
) -> dict:
    wf_config = load_walk_forward_config()
    wf_config["minimum_trades"] = config["minimum_trades"]
    windows = build_walk_forward_windows(df, wf_config)
    windows = windows[: int(config["walk_forward_windows"])]

    if not windows:
        return {
            "pass_rate": 0.0,
            "average_score": 0.0,
            "test_trade_total": 0,
            "windows": 0,
        }

    scores = []
    passes = 0
    test_trade_total = 0

    for window in windows:
        train_best = _score_single_backtest(
            window["train_df"],
            record["strategy"],
            record["original_sl"],
            record["original_tp"],
        )
        test_best = _score_single_backtest(
            window["test_df"],
            copy.deepcopy(record["strategy"]),
            record["original_sl"],
            record["original_tp"],
        )
        score = calculate_walk_forward_score(train_best, test_best, wf_config)
        scores.append(score)
        test_trade_total += int(test_best["Total Trades"])

        if (
            score >= config["pass_score"]
            and int(test_best["Total Trades"]) >= config["minimum_trades"]
        ):
            passes += 1

    return {
        "pass_rate": round(passes / len(windows) * 100, 2),
        "average_score": round(sum(scores) / len(scores), 2),
        "test_trade_total": test_trade_total,
        "windows": len(windows),
    }


def calculate_parameter_sensitivity(
    record: dict,
    df: pd.DataFrame,
    config: dict,
) -> dict:
    neighbors = generate_neighbor_parameters(
        record["parameters"],
        int(config["neighbor_limit"]),
    )

    if not neighbors:
        return {
            "score": 100.0,
            "average_degradation": 0.0,
            "tested_neighbors": 0,
        }

    registry = StrategyTemplateRegistry()
    base_result = _score_single_backtest(
        df,
        record["strategy"],
        record["original_sl"],
        record["original_tp"],
    )
    base_score = _score_report(pd.DataFrame([{
        "Profit Factor": base_result["Profit Factor"],
        "Total PnL %": base_result["Total PnL %"],
        "Win Rate %": base_result["Win Rate %"],
        "Max Drawdown %": base_result["Max Drawdown %"],
        "Trades": base_result["Total Trades"],
    }])).iloc[0]["Overall Score"]
    degradations = []

    for parameters in neighbors:
        candidate_config = registry.build_strategy_config({
            "template_name": record["template_type"],
            "parameters": parameters,
        })
        strategy = create_strategy_from_json_config(candidate_config)
        sl = float(parameters.get("stop_loss_pct", record["original_sl"]))
        tp = float(parameters.get("take_profit_pct", record["original_tp"]))
        neighbor_result = _score_single_backtest(df, strategy, sl, tp)
        neighbor_score = _score_report(pd.DataFrame([{
            "Profit Factor": neighbor_result["Profit Factor"],
            "Total PnL %": neighbor_result["Total PnL %"],
            "Win Rate %": neighbor_result["Win Rate %"],
            "Max Drawdown %": neighbor_result["Max Drawdown %"],
            "Trades": neighbor_result["Total Trades"],
        }])).iloc[0]["Overall Score"]
        degradation = max(0.0, float(base_score) - float(neighbor_score))
        degradations.append(degradation)

    average_degradation = sum(degradations) / len(degradations)
    score = _bounded_score(
        100
        - average_degradation
        / config["maximum_neighbor_degradation_pct"]
        * 100
    )

    return {
        "score": score,
        "average_degradation": round(average_degradation, 2),
        "tested_neighbors": len(neighbors),
    }


def calculate_overfitting_risk(
    walk_forward_result: dict,
    pair_result: dict,
    regime_result: dict,
    parameter_result: dict,
    original_row,
    config: dict,
) -> float:
    risk = 0.0
    risk += (100 - walk_forward_result["pass_rate"]) * 0.30
    risk += (100 - pair_result["score"]) * 0.20
    risk += (100 - regime_result["score"]) * 0.15
    risk += (100 - parameter_result["score"]) * 0.20

    if int(original_row["Trades"]) < config["minimum_trades"]:
        risk += 10

    if abs(float(original_row["Max Drawdown %"])) > config["maximum_drawdown_pct"]:
        risk += 10

    if float(original_row["Profit Factor"]) < config["minimum_profit_factor"]:
        risk += 15

    return _bounded_score(risk)


def calculate_robustness_score(
    walk_forward_result: dict,
    pair_result: dict,
    regime_result: dict,
    parameter_result: dict,
    original_row,
    config: dict,
) -> float:
    pf_score = _bounded_score(float(original_row["Profit Factor"]) / 2 * 100)
    drawdown_score = _bounded_score(
        100
        - abs(float(original_row["Max Drawdown %"]))
        / config["maximum_drawdown_pct"]
        * 100
    )
    trade_score = _bounded_score(
        float(original_row["Trades"]) / (config["minimum_trades"] * 3) * 100
    )
    weighted = (
        walk_forward_result["average_score"] * ROBUSTNESS_WEIGHTS["walk_forward"]
        + pair_result["score"] * ROBUSTNESS_WEIGHTS["pair_consistency"]
        + regime_result["score"] * ROBUSTNESS_WEIGHTS["regime_consistency"]
        + parameter_result["score"] * ROBUSTNESS_WEIGHTS["parameter_sensitivity"]
        + pf_score * ROBUSTNESS_WEIGHTS["profit_factor"]
        + drawdown_score * ROBUSTNESS_WEIGHTS["drawdown"]
        + trade_score * ROBUSTNESS_WEIGHTS["trade_count"]
    ) / sum(ROBUSTNESS_WEIGHTS.values())

    return _bounded_score(weighted)


def determine_status(
    robustness_score: float,
    overfitting_risk_score: float,
    walk_forward_result: dict,
    pair_result: dict,
    parameter_result: dict,
    original_row,
    config: dict,
) -> tuple[str, list[str]]:
    reasons = []

    if float(original_row["Profit Factor"]) < config["minimum_profit_factor"]:
        reasons.append("Profit factor below minimum")

    if int(original_row["Trades"]) < config["minimum_trades"]:
        reasons.append("Trade count below minimum")

    if abs(float(original_row["Max Drawdown %"])) > config["maximum_drawdown_pct"]:
        reasons.append("Drawdown above maximum")

    if walk_forward_result["pass_rate"] < 50:
        reasons.append("Walk-forward pass rate below 50%")

    if pair_result["score"] < 50:
        reasons.append("Pair consistency weak")

    if parameter_result["score"] < 50:
        reasons.append("Neighbor parameter sensitivity high")

    if reasons:
        if robustness_score >= 60 and overfitting_risk_score <= 50:
            return "FRAGILE", reasons
        return "REJECTED", reasons

    if robustness_score >= 75 and overfitting_risk_score <= 30:
        return "ROBUST", []

    if robustness_score >= 60 and overfitting_risk_score <= 50:
        return "PROMISING", []

    if robustness_score >= 45:
        return "FRAGILE", ["Score below robust threshold"]

    return "REJECTED", ["Robustness score too low"]


def _build_shortlist(report: pd.DataFrame, records: list[dict]) -> list[dict]:
    record_map = {record["strategy_id"]: record for record in records}
    shortlist = []

    for _, row in report.iterrows():
        if row["Status"] not in {"ROBUST", "PROMISING"}:
            continue

        record = record_map.get(row["Strategy ID"])
        if not record:
            continue

        shortlist.append({
            "strategy_id": row["Strategy ID"],
            "name": row["Strategy Name"],
            "template_type": row["Template Type"],
            "parameters": record["parameters"],
            "recommended_pairs": [
                pair.strip()
                for pair in str(row["Recommended Pairs"]).split("|")
                if pair.strip()
            ],
            "recommended_regimes": [
                regime.strip()
                for regime in str(row["Recommended Regimes"]).split("|")
                if regime.strip()
            ],
            "robustness_score": row["Robustness Score"],
            "overfitting_risk_score": row["Overfitting Risk Score"],
            "walk_forward_score": row["Average Walk Forward Score"],
            "walk_forward_pass_rate": row["Walk Forward Pass Rate %"] / 100.0,
            "pair_consistency_score": row["Pair Consistency Score"],
            "regime_consistency_score": row["Regime Consistency Score"],
            "profitable_regime_count": row["Profitable Regime Count"],
            "observed_regime_count": row["Observed Regime Count"],
            "regime_attribution_method": row["Regime Attribution Method"],
            "historical_regime_details": record.get("regime_details", []),
            "minimum_expected_metrics": {
                "profit_factor": row["Original Profit Factor"],
                "roi_pct": row["Original ROI %"],
                "win_rate_pct": row["Original Win Rate %"],
                "max_drawdown_pct": row["Original Max Drawdown %"],
                "trades": row["Original Trades"],
                "expectancy": row["Original Expectancy"],
            },
            "notes": "Generated candidate passed robustness validation.",
        })

    return shortlist


def _evaluate_record(
    record: dict,
    original_row,
    comparison_report: pd.DataFrame,
    market_data: dict,
    regime_map: dict,
    trade_report: pd.DataFrame,
    historical_regime_map: dict,
    config: dict,
) -> dict:
    strategy_rows = comparison_report[
        comparison_report["Strategy ID"] == record["strategy_id"]
    ].copy()
    pair_result = calculate_pair_consistency(strategy_rows, config)
    if config.get("historical_regime_attribution_enabled", False):
        candidate_trades = trade_report[
            (trade_report["Strategy ID"] == record["strategy_id"])
            & (trade_report["Pair"] == record["original_pair"])
        ].copy()
        regime_result = calculate_historical_regime_consistency(
            candidate_trades,
            historical_regime_map[record["original_pair"]],
            config,
        )
    else:
        regime_result = calculate_regime_consistency(
            strategy_rows,
            regime_map,
            config,
        )
    record["regime_details"] = regime_result["details"]
    original_df = market_data[record["original_pair"]]
    walk_forward_result = calculate_walk_forward_validation(
        record,
        original_df,
        config,
    )
    parameter_result = calculate_parameter_sensitivity(
        record,
        original_df,
        config,
    )
    overfitting_risk_score = calculate_overfitting_risk(
        walk_forward_result,
        pair_result,
        regime_result,
        parameter_result,
        original_row,
        config,
    )
    robustness_score = calculate_robustness_score(
        walk_forward_result,
        pair_result,
        regime_result,
        parameter_result,
        original_row,
        config,
    )
    status, reasons = determine_status(
        robustness_score,
        overfitting_risk_score,
        walk_forward_result,
        pair_result,
        parameter_result,
        original_row,
        config,
    )

    return {
        "Strategy ID": record["strategy_id"],
        "Strategy Name": record["strategy_name"],
        "Template Type": record["template_type"],
        "Original Pair": record["original_pair"],
        "Original ROI %": round(float(original_row["ROI %"]), 2),
        "Original Profit Factor": round(float(original_row["Profit Factor"]), 2),
        "Original Win Rate %": round(float(original_row["Win Rate %"]), 2),
        "Original Max Drawdown %": round(float(original_row["Max Drawdown %"]), 2),
        "Original Trades": int(original_row["Trades"]),
        "Original Expectancy": round(float(original_row["Expectancy"]), 2),
        "Walk Forward Pass Rate %": walk_forward_result["pass_rate"],
        "Average Walk Forward Score": walk_forward_result["average_score"],
        "Pair Consistency Score": pair_result["score"],
        "Regime Consistency Score": regime_result["score"],
        "Profitable Regime Count": len(regime_result["recommended_regimes"]),
        "Observed Regime Count": regime_result["observed_regime_count"],
        "Regime Attribution Method": regime_result["method"],
        "Parameter Sensitivity Score": parameter_result["score"],
        "Overfitting Risk Score": overfitting_risk_score,
        "Robustness Score": robustness_score,
        "Status": status,
        "Rejection Reasons": " | ".join(reasons),
        "Recommended Pairs": " | ".join(pair_result["recommended_pairs"]),
        "Recommended Regimes": " | ".join(regime_result["recommended_regimes"]),
    }


def run_generated_strategy_robustness(config_override: dict | None = None):
    config = load_robustness_config()
    if config_override:
        config.update(config_override)

    if not config.get("enabled", False):
        print("Generated strategy robustness validation disabled by config.")
        return pd.DataFrame(columns=REPORT_COLUMNS), []

    comparison_report = _load_comparison_report(config["comparison_report"])
    top_candidates = select_top_generated_candidates(
        comparison_report,
        int(config["top_candidate_count"]),
        config["pairs"],
    )
    if top_candidates.empty:
        report = pd.DataFrame(columns=REPORT_COLUMNS)
        shortlist = []
        save_csv_report(report, config["output_report"])
        save_json_report(shortlist, config["shortlist_report"])
        return report, shortlist

    generator_limit = max(
        int(config["top_candidate_count"]) * 4,
        int(config.get("generated_candidate_limit", 30)),
    )
    atr_exit_variants = config.get("atr_exit_variants")
    if atr_exit_variants is None:
        atr_exit_variants = load_experiment_config().get("atr_exit_variants")
    records = resolve_top_candidate_records(
        top_candidates,
        generator_limit,
        atr_exit_variants,
    )
    records = _apply_validation_task_cap(records, config)

    if not records:
        raise ValueError("No top generated candidate records could be resolved")

    pairs = config["pairs"]
    comparison_report = comparison_report[
        comparison_report["Pair"].isin(pairs)
    ].copy()
    market_data = load_market_data(
        pairs,
        config["timeframe"],
        config["lookback"],
    )
    regime_map = _build_regime_map(market_data)
    trade_report = pd.DataFrame()
    historical_regime_map = {}
    if config.get("historical_regime_attribution_enabled", False):
        trade_path = config.get("trade_report")
        if not trade_path:
            raise ValueError(
                "Historical regime attribution requires a candidate trade report"
            )
        trade_report = _load_trade_report(trade_path)
        regime_config = load_market_regime_config()
        required_regime_pairs = {
            record["original_pair"]
            for record in records
        }
        historical_regime_map = {
            pair: detect_historical_market_regimes(df, regime_config)
            for pair, df in market_data.items()
            if pair in required_regime_pairs
        }
    rows = []
    total = len(records)

    print("\n===== B TRADER GENERATED STRATEGY ROBUSTNESS =====")
    print(f"Top candidates: {total}")

    for index, record in enumerate(records, start=1):
        original_row = top_candidates[
            top_candidates["Strategy ID"] == record["strategy_id"]
        ].iloc[0]
        print(
            f"Validating {index}/{total}: "
            f"{record['strategy_id']} | {record['original_pair']}"
        )
        rows.append(_evaluate_record(
            record,
            original_row,
            comparison_report,
            market_data,
            regime_map,
            trade_report,
            historical_regime_map,
            config,
        ))

    report = pd.DataFrame(rows)
    report = report.sort_values(
        by=["Robustness Score", "Overfitting Risk Score", "Original ROI %"],
        ascending=[False, True, False],
    )
    save_csv_report(report, config["output_report"])

    shortlist = _build_shortlist(report, records)
    save_json_report(shortlist, config["shortlist_report"])

    print(f"\nRobustness report saved -> {config['output_report']}")
    print(f"Shortlist saved -> {config['shortlist_report']}")
    print(report[REPORT_COLUMNS].to_string(index=False))

    return report, shortlist


if __name__ == "__main__":
    run_generated_strategy_robustness()
