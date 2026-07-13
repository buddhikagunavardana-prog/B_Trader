"""Deterministic, artifact-driven progressive research candidate funnel."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.pipeline.pipeline_loader import load_json_config


CONFIG_PATH = Path("src/config/progressive_research_funnel.json")
CANDIDATE_KEYS = ["Strategy ID", "Pair"]


@dataclass(frozen=True)
class FunnelStage:
    name: str
    history_months: int
    partitions: tuple[dict, ...]


def load_funnel_config(config_path: Path = CONFIG_PATH) -> dict:
    config = load_json_config(config_path, [
        "enabled", "minimum_trades", "minimum_profit_factor",
        "maximum_drawdown_pct", "stages",
    ])
    if int(config["minimum_trades"]) < 1:
        raise ValueError("minimum_trades must be positive")
    if float(config["minimum_profit_factor"]) <= 0:
        raise ValueError("minimum_profit_factor must be positive")
    if float(config["maximum_drawdown_pct"]) <= 0:
        raise ValueError("maximum_drawdown_pct must be positive")
    names = set()
    for raw in config["stages"]:
        stage = parse_stage(raw)
        if stage.name in names:
            raise ValueError(f"Duplicate funnel stage: {stage.name}")
        names.add(stage.name)
        if sum(int(item["months"]) for item in stage.partitions) != stage.history_months:
            raise ValueError(f"Partition months do not match history for {stage.name}")
    return config


def funnel_config_hash(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_stage(raw: dict) -> FunnelStage:
    required = {"name", "history_months", "partitions"}
    missing = required.difference(raw)
    if missing:
        raise ValueError(f"Missing funnel stage fields: {sorted(missing)}")
    history_months = int(raw["history_months"])
    partitions = tuple(dict(item) for item in raw["partitions"])
    if history_months < 1 or not partitions:
        raise ValueError("Funnel stage history and partitions must be non-empty")
    if any(int(item.get("months", 0)) < 1 or not item.get("name") for item in partitions):
        raise ValueError("Each funnel partition requires a name and positive months")
    return FunnelStage(str(raw["name"]), history_months, partitions)


def _metrics(pnl: pd.Series) -> dict:
    values = pd.to_numeric(pnl, errors="coerce").dropna().to_numpy(dtype=float)
    if not len(values):
        return {"trades": 0, "profit_factor": 0.0, "max_drawdown_pct": 0.0}
    gross_profit = values[values > 0].sum()
    gross_loss = abs(values[values < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
    equity = np.cumprod(1.0 + values / 100.0)
    peaks = np.maximum.accumulate(np.concatenate(([1.0], equity)))[:-1]
    drawdown = (equity / peaks - 1.0) * 100.0
    return {
        "trades": int(len(values)),
        "profit_factor": round(float(profit_factor), 6),
        "max_drawdown_pct": round(abs(float(min(drawdown.min(), 0.0))), 6),
    }


def evaluate_funnel_stage(
    candidates: pd.DataFrame,
    trades: pd.DataFrame,
    stage_config: dict,
    config: dict,
) -> pd.DataFrame:
    """Evaluate candidates without re-scoring or mutating their source columns."""
    stage = parse_stage(stage_config)
    required_candidate = set(CANDIDATE_KEYS)
    required_trade = required_candidate | {"Entry Time", "PnL %"}
    if not required_candidate.issubset(candidates.columns):
        raise ValueError("Candidate artifact is missing Strategy ID or Pair")
    if not required_trade.issubset(trades.columns):
        raise ValueError("Trade artifact is missing funnel contract columns")
    if pd.api.types.is_numeric_dtype(trades["Entry Time"]):
        raise ValueError(
            "Trade artifact Entry Time must contain calendar timestamps, "
            "not row indices"
        )

    work = trades.copy()
    work["Entry Time"] = pd.to_datetime(work["Entry Time"], utc=True, errors="coerce")
    work = work.dropna(subset=["Entry Time"])
    end = work["Entry Time"].max()
    if pd.isna(end):
        end = pd.Timestamp.now(tz="UTC")
    start = end - pd.DateOffset(months=stage.history_months)
    boundaries = [start]
    for partition in stage.partitions:
        boundaries.append(boundaries[-1] + pd.DateOffset(months=int(partition["months"])))
    boundaries[-1] = end + pd.Timedelta(microseconds=1)

    rows = []
    unique = candidates.drop_duplicates(CANDIDATE_KEYS, keep="first")
    for _, candidate in unique.sort_values(CANDIDATE_KEYS).iterrows():
        selected = work[
            (work["Strategy ID"] == candidate["Strategy ID"])
            & (work["Pair"] == candidate["Pair"])
        ]
        passed = True
        row = candidate.to_dict()
        reasons = []
        for index, partition in enumerate(stage.partitions):
            segment = selected[
                (selected["Entry Time"] >= boundaries[index])
                & (selected["Entry Time"] < boundaries[index + 1])
            ]
            metrics = _metrics(segment["PnL %"])
            prefix = str(partition["name"])
            row[f"{prefix}_trades"] = metrics["trades"]
            row[f"{prefix}_profit_factor"] = metrics["profit_factor"]
            row[f"{prefix}_max_drawdown_pct"] = metrics["max_drawdown_pct"]
            if partition.get("required_to_pass", False):
                checks = [
                    (metrics["trades"] >= int(config["minimum_trades"]), "trades"),
                    (metrics["profit_factor"] >= float(config["minimum_profit_factor"]), "profit_factor"),
                    (metrics["max_drawdown_pct"] <= float(config["maximum_drawdown_pct"]), "drawdown"),
                ]
                for valid, label in checks:
                    if not valid:
                        passed = False
                        reasons.append(f"{prefix}:{label}")
        row.update({
            "Funnel Stage": stage.name,
            "Funnel Status": "PASS" if passed else "REJECT",
            "Funnel Rejection Reasons": " | ".join(reasons),
            "Funnel Window Start": start.isoformat(),
            "Funnel Window End": end.isoformat(),
        })
        rows.append(row)
    return pd.DataFrame(rows)
