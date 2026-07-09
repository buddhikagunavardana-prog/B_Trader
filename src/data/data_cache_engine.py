from pathlib import Path
import re

import pandas as pd

from src.plugins.binance_data import download_klines


CACHE_DIR = Path("data/cache/binance")


def _safe_cache_part(value) -> str:
    text = str(value or "none").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "none"


def _cache_path(symbol: str, timeframe: str, lookback: str, limit=None) -> Path:
    parts = [
        _safe_cache_part(symbol),
        _safe_cache_part(timeframe),
        _safe_cache_part(lookback),
        _safe_cache_part(limit),
    ]
    return CACHE_DIR / ("_".join(parts) + ".csv")


def _normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    for column in ["open_time", "close_time"]:
        if column in normalized.columns:
            normalized[column] = pd.to_datetime(normalized[column])

    for column in ["open", "high", "low", "close", "volume"]:
        if column in normalized.columns:
            normalized[column] = normalized[column].astype(float)

    return normalized


def get_cached_klines(
    symbol: str,
    timeframe: str,
    lookback: str = "1 year ago UTC",
    limit=None,
) -> pd.DataFrame:
    cache_file = _cache_path(symbol, timeframe, lookback, limit)

    if cache_file.exists():
        print(f"  Cache hit: {cache_file}")
        return _normalize_ohlcv_df(pd.read_csv(cache_file))

    print(f"  Cache miss: downloading {symbol} {timeframe} {lookback}")
    df = download_klines(
        symbol=symbol,
        interval=timeframe,
        start_str=lookback,
    )

    if limit is not None:
        df = df.tail(int(limit))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_file, index=False)

    return _normalize_ohlcv_df(df)
