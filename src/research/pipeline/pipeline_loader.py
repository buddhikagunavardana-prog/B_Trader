import json
from pathlib import Path
from typing import Callable

import pandas as pd

from src.data.data_cache_engine import get_cached_klines


def load_json_config(
    config_path: Path,
    required_keys: list[str] | None = None,
    defaults: dict | None = None,
) -> dict:
    config = dict(defaults or {})

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as file:
            config.update(json.load(file))

    for key in required_keys or []:
        if key not in config:
            raise ValueError(f"Missing config key: {key}")

    return config


def load_csv_report(path: str, required_columns: set[str] | None = None) -> pd.DataFrame:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {path}")

    report = pd.read_csv(report_path)
    missing = (required_columns or set()) - set(report.columns)

    if missing:
        raise ValueError(f"Report missing columns: {sorted(missing)}")

    return report


def load_market_data(
    pairs: list[str],
    timeframe: str,
    lookback: str,
    data_loader: Callable = get_cached_klines,
    logger: Callable[[str], None] | None = None,
) -> dict[str, pd.DataFrame]:
    market_data = {}

    for pair in pairs:
        if logger:
            logger(f"Loading cached data: {pair} | Timeframe: {timeframe}")

        market_data[pair] = data_loader(pair, timeframe, lookback)

    return market_data
