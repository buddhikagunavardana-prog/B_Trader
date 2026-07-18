from __future__ import annotations

import time
import ctypes
from pathlib import Path

import numpy as np
import pandas as pd

from src.indicators.registry import indicator_registry


REPORT_PATH = Path("reports/indicator_performance_validation.csv")
ROW_COUNTS = (1_000, 10_000, 50_000)
REPETITIONS = 3


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _working_set_mib() -> float:
    """Return current Windows process working set, or NaN if unavailable."""
    try:
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        process = kernel.GetCurrentProcess()
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        query.restype = ctypes.c_int
        success = query(
            process, ctypes.byref(counters), counters.cb,
        )
        return counters.WorkingSetSize / (1024 * 1024) if success else float("nan")
    except (AttributeError, OSError):
        return float("nan")


def _market(rows: int) -> pd.DataFrame:
    rng = np.random.default_rng(2350 + rows)
    returns = rng.normal(0.0001, 0.01, rows)
    close = 100.0 * np.exp(np.cumsum(returns))
    spread = rng.uniform(0.001, 0.02, rows) * close
    return pd.DataFrame({
        "open": close * (1.0 + rng.normal(0.0, 0.002, rows)),
        "high": close + spread,
        "low": close - spread,
        "close": close,
        "volume": rng.lognormal(8.0, 0.7, rows),
    }, index=pd.date_range("2026-01-01", periods=rows, freq="min"))


def _run_once(market: pd.DataFrame, names: list[str]) -> tuple[float, dict[str, float]]:
    per_name = {}
    started = time.perf_counter()
    for name in names:
        indicator_started = time.perf_counter()
        indicator_registry.calculate(name, market)
        per_name[name] = time.perf_counter() - indicator_started
    return time.perf_counter() - started, per_name


def run_performance_validation() -> pd.DataFrame:
    """Benchmark the complete registry and approximate Python allocation peaks."""
    names = indicator_registry.list_names()
    rows = []
    previous_time = None
    previous_size = None
    for row_count in ROW_COUNTS:
        market = _market(row_count)
        memory_before = _working_set_mib()
        _run_once(market, names)
        measured = []
        cumulative = {name: 0.0 for name in names}
        memory_peak = max(memory_before, _working_set_mib())
        for _ in range(REPETITIONS):
            elapsed, per_name = _run_once(market, names)
            measured.append(elapsed)
            memory_peak = max(memory_peak, _working_set_mib())
            for name, value in per_name.items():
                cumulative[name] += value
        average = float(np.mean(measured))
        slowest = sorted(cumulative.items(), key=lambda item: item[1], reverse=True)[:10]
        scaling = "BASELINE"
        suspicious = []
        if previous_time is not None and previous_size is not None:
            time_ratio = average / previous_time
            row_ratio = row_count / previous_size
            scaling = f"{time_ratio:.3f}x time for {row_ratio:.1f}x rows"
            if time_ratio > row_ratio * 1.35:
                suspicious.append("aggregate superlinear scaling")
        rows.append({
            "Rows": row_count,
            "Indicator Count": len(names),
            "Run 1 Seconds": measured[0],
            "Run 2 Seconds": measured[1],
            "Run 3 Seconds": measured[2],
            "Average Seconds": average,
            "Average Per Indicator Seconds": average / len(names),
            "Approx Process Memory Increase MiB": max(memory_peak - memory_before, 0.0),
            "Slowest Ten": "; ".join(f"{name}={value / REPETITIONS:.6f}s" for name, value in slowest),
            "Scaling vs Previous": scaling,
            "Suspicious Nonlinear Scaling": "; ".join(suspicious) or "NONE",
            "Status": "PASS WITH WARNING" if suspicious else "PASS",
            "Notes": "working-set delta sampled after each full-library repetition; transient intra-indicator peaks may be higher",
        })
        previous_time, previous_size = average, row_count
    return pd.DataFrame(rows)


def write_performance_validation(path: Path = REPORT_PATH) -> Path:
    """Write deterministic multi-size performance results."""
    path.parent.mkdir(parents=True, exist_ok=True)
    run_performance_validation().to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_performance_validation())
