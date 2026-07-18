from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
from src.trading_frameworks.registry import trading_framework_registry


REPORT_PATH = Path("reports/trading_framework_performance.csv")


def _precomputed_frame(rows: int, freq: str = "5min") -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq=freq, tz="UTC")
    base = np.linspace(100.0, 120.0, rows)
    return pd.DataFrame({
        "high": base + 1, "low": base - 1, "close": base, "volume": np.full(rows, 1500.0),
        "EMA": base - 1, "MACD": np.ones(rows), "MACD_SIGNAL": np.zeros(rows), "MACD_HISTOGRAM": np.ones(rows), "RSI": np.full(rows, 25.0),
        "STOCHASTIC_K": np.full(rows, 20.0), "FORCE_INDEX": np.ones(rows), "ATR": np.full(rows, 1.5),
        "DONCHIAN_UPPER": base + 2, "DONCHIAN_LOWER": base - 2,
        "DONCHIAN_EXIT_UPPER": base + 1, "DONCHIAN_EXIT_LOWER": base - 1,
        "ICHIMOKU_CONVERSION": base - .5, "ICHIMOKU_BASE": base - 1,
        "ICHIMOKU_SPAN_A": base - 2, "ICHIMOKU_SPAN_B": base - 3, "ICHIMOKU_LAGGING": base - .5,
        "BOLLINGER_UPPER": base + 2, "BOLLINGER_MIDDLE": base, "BOLLINGER_LOWER": base - 2,
        "KELTNER_UPPER": base + 1.5, "KELTNER_MIDDLE": base, "KELTNER_LOWER": base - 1.5,
        "ZSCORE": np.zeros(rows), "ADX": np.full(rows, 22.0), "VOLUME_SMA": np.full(rows, 1000.0),
        "SUPERTREND": base - 1, "SUPERTREND_DIRECTION": np.ones(rows),
        "EMA_8": base-0.1, "EMA_13": base-0.2, "EMA_21": base-0.3, "EMA_34": base-0.4, "EMA_55": base-0.5,
        "EMA_FAST": base-0.1, "EMA_SLOW": base-0.2, "PLUS_DI": np.full(rows, 30.0), "MINUS_DI": np.full(rows, 15.0),
        "PARABOLIC_SAR": base-1, "PARABOLIC_SAR_DIRECTION": np.ones(rows),
        "BOLLINGER_BAND_WIDTH": np.full(rows, .04), "VWAP": base, "VWAP_DEVIATION": np.zeros(rows),
        "SUPPORT": base-1, "RESISTANCE": base+1, "SWING_HIGH": base+1, "SWING_LOW": base-1,
    }, index=index)


def _context(name: str, rows: int) -> FrameworkContext:
    if name == "triple_screen_trading":
        return FrameworkContext({
            "trend": _precomputed_frame(max(2, rows // 12), "1h"),
            "setup": _precomputed_frame(max(2, rows // 3), "15min"),
            "entry": _precomputed_frame(rows, "5min"),
        })
    return FrameworkContext({"execution": _precomputed_frame(rows)})


def benchmark_trading_frameworks(row_counts: tuple[int, ...] = (1_000, 10_000), measured_runs: int = 3) -> pd.DataFrame:
    results = []
    for rows in row_counts:
        for name in trading_framework_registry.list_names():
            framework = load_trading_framework(name)
            context = _context(name, rows)
            framework.execute(context)  # one warm-up
            timings = []
            for _ in range(measured_runs):
                started = perf_counter()
                framework.execute(context)
                timings.append((perf_counter() - started) * 1000.0)
            memory = sum(frame.memory_usage(deep=True).sum() for frame in context.frames.values())
            results.append({
                "Rows": rows, "Framework": name,
                "Average Runtime Ms": round(sum(timings) / len(timings), 6),
                "Minimum Runtime Ms": round(min(timings), 6),
                "Maximum Runtime Ms": round(max(timings), 6),
                "Measured Runs": measured_runs, "Warmup Runs": 1,
                "Precomputed Input Memory Bytes": int(memory),
                "Repeated Indicator Calculation": "No",
            })
    return pd.DataFrame(results)


def write_performance_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_trading_frameworks().to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_performance_report())
