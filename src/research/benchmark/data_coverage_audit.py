from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import CACHE_DIR
from src.research.pipeline.pipeline_reporter import save_csv_report


COVERAGE_COLUMNS = [
    "Pair",
    "Timeframe",
    "Earliest Timestamp",
    "Latest Timestamp",
    "Available Days",
    "Available Years",
    "Expected Candles",
    "Actual Candles",
    "Missing Candle Estimate",
    "Duplicate Count",
    "Invalid Row Count",
    "Coverage Status",
    "Notes",
]


def _cache_file(pair: str, timeframe: str, lookback: str = "1_year_ago_utc") -> Path:
    return CACHE_DIR / f"{pair.lower()}_{timeframe.lower()}_{lookback}_none.csv"


def _timeframe_minutes(timeframe: str) -> int:
    if timeframe.endswith("m"):
        return int(timeframe[:-1])
    if timeframe.endswith("h"):
        return int(timeframe[:-1]) * 60
    if timeframe.endswith("d"):
        return int(timeframe[:-1]) * 1440
    raise ValueError(f"Unsupported timeframe for coverage audit: {timeframe}")


def _invalid_row_count(df: pd.DataFrame) -> int:
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        return len(df)

    invalid = df[required].isna().any(axis=1)
    invalid |= (df["high"] < df["low"])
    invalid |= (df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)
    invalid |= df["volume"] < 0
    return int(invalid.sum())


def audit_pair_timeframe(
    pair: str,
    timeframe: str,
    cache_dir: str | Path = CACHE_DIR,
) -> dict:
    cache_path = Path(cache_dir) / _cache_file(pair, timeframe).name
    if not cache_path.exists():
        return {
            "Pair": pair,
            "Timeframe": timeframe,
            "Earliest Timestamp": "",
            "Latest Timestamp": "",
            "Available Days": 0.0,
            "Available Years": 0.0,
            "Expected Candles": 0,
            "Actual Candles": 0,
            "Missing Candle Estimate": 0,
            "Duplicate Count": 0,
            "Invalid Row Count": 0,
            "Coverage Status": "MISSING_CACHE",
            "Notes": f"Cache file not found: {cache_path}",
        }

    df = pd.read_csv(cache_path, parse_dates=["open_time", "close_time"])
    if df.empty:
        return {
            "Pair": pair,
            "Timeframe": timeframe,
            "Earliest Timestamp": "",
            "Latest Timestamp": "",
            "Available Days": 0.0,
            "Available Years": 0.0,
            "Expected Candles": 0,
            "Actual Candles": 0,
            "Missing Candle Estimate": 0,
            "Duplicate Count": 0,
            "Invalid Row Count": 0,
            "Coverage Status": "EMPTY_CACHE",
            "Notes": f"Cache file is empty: {cache_path}",
        }

    timestamp_column = "open_time" if "open_time" in df.columns else df.columns[0]
    earliest = pd.to_datetime(df[timestamp_column]).min()
    latest = pd.to_datetime(df[timestamp_column]).max()
    actual = len(df)
    minutes = _timeframe_minutes(timeframe)
    available_days = max((latest - earliest).total_seconds() / 86400, 0.0)
    expected = int(available_days * 1440 / minutes) + 1 if available_days else actual
    duplicate_count = int(df.duplicated(subset=[timestamp_column]).sum())
    invalid_count = _invalid_row_count(df)
    missing_estimate = max(expected - actual + duplicate_count, 0)

    notes = []
    status = "OK"
    if missing_estimate > 0:
        status = "GAPS_DETECTED"
        notes.append("missing candle estimate above zero")
    if duplicate_count > 0:
        status = "DATA_QUALITY_WARNING"
        notes.append("duplicate candles detected")
    if invalid_count > 0:
        status = "DATA_QUALITY_WARNING"
        notes.append("invalid OHLCV rows detected")
    if available_days < 180:
        status = "INSUFFICIENT_HISTORY"
        notes.append("less than 180 days available")

    return {
        "Pair": pair,
        "Timeframe": timeframe,
        "Earliest Timestamp": earliest.isoformat(),
        "Latest Timestamp": latest.isoformat(),
        "Available Days": round(available_days, 2),
        "Available Years": round(available_days / 365.25, 3),
        "Expected Candles": expected,
        "Actual Candles": actual,
        "Missing Candle Estimate": missing_estimate,
        "Duplicate Count": duplicate_count,
        "Invalid Row Count": invalid_count,
        "Coverage Status": status,
        "Notes": " | ".join(notes),
    }


def run_data_coverage_audit(
    pairs: list[str],
    timeframes: list[str],
    output_report: str = "reports/data_coverage_audit.csv",
    cache_dir: str | Path = CACHE_DIR,
) -> pd.DataFrame:
    rows = [
        audit_pair_timeframe(pair, timeframe, cache_dir)
        for pair in pairs
        for timeframe in timeframes
    ]
    report = pd.DataFrame(rows, columns=COVERAGE_COLUMNS)
    save_csv_report(report, output_report)
    return report


if __name__ == "__main__":
    default_pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    run_data_coverage_audit(default_pairs, ["15m"])
