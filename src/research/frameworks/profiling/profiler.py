from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.profiling.aggregation import timing_statistics
from src.research.frameworks.profiling.memory import result_memory
from src.research.frameworks.profiling.models import ExecutionMode, ProfileMeasurement
from src.trading_frameworks.loader import load_trading_framework


def _mode_configuration(configuration, mode: ExecutionMode):
    stateful = mode is not ExecutionMode.STATELESS
    instrumented = mode is ExecutionMode.STATEFUL_POLICY_INSTRUMENTED
    return replace(configuration, enable_stateful_research=stateful, enable_controller_timing=instrumented, run_id=None)


def profile_framework(configuration, sources, mode=ExecutionMode.STATEFUL_POLICY, warmup_runs=1, measured_runs=5):
    mode = ExecutionMode(mode)
    configured = _mode_configuration(configuration, mode)
    for _ in range(warmup_runs):
        run_framework_decision_series(configured, sources)
    elapsed = []
    results = []
    for _ in range(measured_runs):
        started = perf_counter()
        result = run_framework_decision_series(configured, sources)
        elapsed.append(perf_counter() - started)
        results.append(result)
    statistics = timing_statistics(elapsed)
    repro = [result.reproducibility for result in results]
    average = lambda key: sum(float(item.get(key, 0)) for item in repro) / measured_runs
    timing = results[-1].summary.get("controller_timing_ns", {})
    memory = result_memory(results[-1], sources)
    framework = load_trading_framework(configured.framework, configured.parameters)
    return ProfileMeasurement(
        configured.framework, framework.metadata.category, len(results[-1].decisions), mode.value,
        configured.enable_controller_timing, warmup_runs, measured_runs, **statistics,
        preparation_ms=average("preparation_seconds") * 1000,
        alignment_ms=average("alignment_seconds") * 1000,
        decision_ms=average("framework_decision_seconds") * 1000,
        controller_ms=average("controller_time_ns") / 1_000_000,
        policy_ms=average("policy_time_ns") / 1_000_000,
        session_ms=float(timing.get("session_policy_time_ns", 0)) / 1_000_000,
        setup_ms=float(timing.get("setup_policy_time_ns", 0)) / 1_000_000,
        position_ms=float(timing.get("position_policy_time_ns", 0)) / 1_000_000,
        diagnostics_ms=average("diagnostics_seconds") * 1000,
        normalization_ms=average("normalization_seconds") * 1000,
        serialization_ms=average("serialization_seconds") * 1000,
        manifest_ms=average("manifest_seconds") * 1000,
        memory_bytes=memory["estimated_total_bytes"],
        repeated_indicator_calculations=int(repro[-1].get("repeated_indicator_calculation_count", 0)),
    )
