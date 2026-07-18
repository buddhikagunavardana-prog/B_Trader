# Framework Research Adapter

## Phase 24.6 coverage

The adapter loads and normalizes all 35 canonical frameworks. The fifteen new frameworks use the same causal alignment, run-local state controller, policy reason codes, configuration identity, and manifest structure. Multi-component dependency requests store canonical name, component, alias, parameter fingerprint, and provenance; equivalent requests calculate once. Prior-session pivots use only completed prior session groups and deterministic IDs.

## Phase 24.5 proposal-policy-controller flow

Stateful mode passes each framework proposal through the policy layer before the controller applies it. Optional output fields cover policy permission/reason, setup expiry/invalidation, opposite action, cooldown, maximum hold, rollover cleanup, level lifecycle, and controller timing. Stateless mode and original decision columns remain unchanged. Policy settings are reproducibility inputs; measured timing remains outside stable identity.

## Scope

Phase 24.2 converts the point-in-time decisions introduced in Phase 24.1 into deterministic chronological decision series. It is a structural research foundation only. It does not download data, resample inside a framework, model fills, place orders, size positions, simulate balances, or calculate profitability metrics.

```text
Prepared OHLCV + indicators -> causal role alignment -> framework decision
                           -> normalized decision series -> validation/reporting
```

## Configuration

`FrameworkResearchConfiguration` is a versioned, JSON-safe configuration containing framework identity/version, validated parameter overrides, placeholder market identity, exact timeframe-role mapping, primary timeline role, date bounds, warm-up policy, output options, experimental opt-in, preparation mode, seed, and deterministic run identifier. Unknown fields and unsupported schema versions are rejected. Five safe examples live in `src/config/framework_research/` and use `SYNTHETIC-USD`.

`allow_experimental` defaults to `false`. An experimental framework or required experimental indicator is rejected without explicit opt-in. Opted-in runs carry a warning and are never described as production-ready.

## Data preparation

`PRECOMPUTED_ONLY` is the default. It validates role completeness, role-specific required columns, unique chronological `DatetimeIndex` values, and source preservation. Naive indexes are interpreted as UTC and timezone-aware indexes are converted to UTC. Infinite numeric values are converted to `NaN` with a recorded warning so they cannot silently become valid decisions.

`COMPUTE_MISSING` must be selected explicitly. It computes only absent required outputs through the canonical indicator registry. Turtle and Donchian entry/exit channels are computed once with their separately configured periods. Indicator computation happens during preparation, never in the per-row decision loop. Neither mode downloads or resamples data.

Prepared-role metadata records row count, first/last valid timestamp, warm-up rows, indicator columns, computed columns, timezone, warnings, and preparation mode.

## Causal alignment

The primary role supplies the decision timeline. Every other role uses a backward/as-of lookup (`searchsorted(..., side="right")`), so the source timestamp is always at or before the decision timestamp. Exact close timestamps are visible; a bar whose close lies in the future is not. Missing and stale bars remain explicit rather than being filled from the future.

Each row can retain role-level source timestamps, completed-bar flags, missing-role flags, stale age in seconds, and alignment warnings. Causal prefix views are passed to `execute_prepared`; source frames were already validated once, avoiding repeated historical scans while preserving the Phase 24.1 framework contract.

## Adapter API

```python
from src.research.frameworks import (
    FrameworkResearchConfiguration,
    run_framework_decision_series,
)

config = FrameworkResearchConfiguration(
    framework="triple_screen_trading",
    framework_version="1.0.0",
    parameters={},
    symbol="SYNTHETIC-USD",
    market_type="crypto_spot",
    timeframe_roles={"trend": "1h", "setup": "15m", "entry": "5m"},
    primary_role="entry",
)
result = run_framework_decision_series(config, {
    "trend": precomputed_1h,
    "setup": precomputed_15m,
    "entry": precomputed_5m,
})
```

The adapter validates configuration, prepares data without mutating sources, precomputes causal role positions, iterates chronologically, records warm-up skips, normalizes decisions, validates output, and returns `DecisionSeriesResult` with timing and reproducibility metadata.

## Normalized decision schema

Every output uses: timestamp, framework/version, signal/direction, entry and exit flags/reasons, confidence, stop type/value/distance, target type/value, reward-to-risk, trailing-stop type, risk-fraction suggestion, maximum-holding hint, JSON diagnostics/warnings/row availability, warm-up status, decision validity, and skip reason. Framework-specific diagnostics are retained. Warm-up rows default to a marked `NO_TRADE` row with `decision_valid=false` and `skip_reason=warmup_incomplete`.

## Validation and summaries

Structured validation checks required columns, chronological uniqueness, enums, finite numeric fields, JSON-safe nested values, skip reasons, and suspicious primary-timeline gaps. Tests additionally verify deterministic repeatability, source non-mutation, exact higher-timeframe boundaries, and all-five-framework future-change invariance through both preparation modes.

Allowed summaries are counts of timeline/evaluated/skipped/warm-up and signal/direction states, entry/exit flags, confidence, warnings, stale ages, and execution duration. PnL, ROI, win rate, profit factor, drawdown, Sharpe ratio, balance, and trade profitability are deliberately absent.

## Synthetic scenarios and reports

Deterministic fixtures cover strong up/down trends, sideways range, volatility and false breakouts, bullish pullback, bearish rally, sparse higher-timeframe bars, missing-bar gaps, exact closing boundaries, zero/low volatility, gap events, and short warm-up histories. These scenarios check structure and behavior only.

Release artifacts are:

- `reports/framework_research_adapter_inventory.csv`
- `reports/framework_decision_series_validation.csv`
- `reports/framework_research_adapter_performance.csv`

Performance reporting separates preparation, alignment, decision-series generation, total runtime, rows per second, retained input memory, and repeated indicator calculations.

## Limitations and next integration

The adapter does not infer fills or broker positions. Phase 24.4 adds a separate advisory research-state controller so exit-capable framework decisions can receive prior signal context without simulating execution. Missing-bar policy remains explicit and runtime decision files are not committed.

Stateful research is enabled by a backward-compatible configuration default and may be disabled for the original stateless output. State columns are appended; existing normalized columns and framework APIs remain unchanged. See `framework_research_state.md`.

## Phase 24.3 expansion and manifests

The adapter now validates twenty framework configurations without changing its normalized output. `build_reproducibility_manifest()` separates deterministic configuration/input fields and their stable hash from runtime commit, execution timestamp, and warnings. Manifests contain no decisions, credentials, fills, or profitability fields and may optionally be written to an ignored runtime location. Streaming output remains out of scope.
