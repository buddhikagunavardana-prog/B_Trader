from __future__ import annotations

from statistics import mean, median, pstdev


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def timing_statistics(seconds: list[float]) -> dict[str, float]:
    milliseconds = [value * 1000.0 for value in seconds]
    return {
        "mean_ms": mean(milliseconds),
        "median_ms": median(milliseconds),
        "minimum_ms": min(milliseconds),
        "maximum_ms": max(milliseconds),
        "standard_deviation_ms": pstdev(milliseconds),
        "p90_ms": percentile(milliseconds, 0.90),
    }
