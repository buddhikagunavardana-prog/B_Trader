# Framework Performance Architecture

Phase 24.7 profiles the complete 35-framework research path without network, execution, or profitability behavior. Profiling is optional and disabled during ordinary adapter runs. `FrameworkRuntimeContext` is immutable and run-scoped; it resolves the configuration fingerprint, dependency fingerprints, diagnostic level, snapshot mode, row count, instrumentation flag, prepared frames, and deterministic session snapshots once per run. It is never a global cache and owns no mutable position or setup state.

## Measured baseline and optimized result

The authoritative Phase 24.6 10,000-row stateful-policy reference was 5,048.367 ms/framework. The Phase 24.7 five-run median average is 3,390.445 ms/framework, a 32.84% improvement. Instrumented median average is 3,414.664 ms, or 0.714% aggregate overhead. The 1,000-to-10,000-row ratio is 9.581x and repeated indicator calculations remain zero.

The slowest optimized 10,000-row stateful-policy frameworks are Stochastic Pullback Trend (4,746.475 ms), CCI Trend Pullback (4,572.724 ms), Williams Percent R Reversal (4,550.625 ms), Triple Screen Trading (4,213.072 ms), and Pin Bar Rejection (4,070.476 ms). Framework decision construction remains the dominant cost. Diagnostics and normalization are secondary; manifest construction is negligible.

## Structural optimizations

The adapter now validates prepared frames once and uses an internal runtime execution path instead of repeating role, column, timestamp, and future-row validation for every decision. It still passes causal prefix slices, so completed-bar behavior is unchanged. The controller pre-resolves setup/event/session framework membership and the immutable rollover policy once rather than performing membership checks and dataclass replacement per row.

Session configuration parsing, timezone objects, time boundaries, opening-range duration, entry cutoff, and deterministic IDs are resolved once into a session context array. Contexts are never shared when configuration fingerprints differ. Opening Range Breakout receives causal, run-owned opening-high/low/completion columns computed in one bounded scan; direct framework use retains the legacy causal fallback. This removes its repeated intraday range scan without altering its trigger bar or values.

Instrumentation totals no longer serialize a timing dataclass on every row. Normalized output columns, index order, NaN behavior, policy reason codes, setup IDs, and risk proposals are unchanged. Timing fields remain the only nondeterministic output fields.

## Diagnostics and snapshots

Diagnostic levels are `none`, `summary`, `standard`, and `full`. `standard` remains the default and preserves Phase 24.6 behavior. Diagnostic detail changes payload storage only; signal, direction, risk, setup, position, session, policy, validity, warning, and skip fields are invariant.

Snapshot modes are `none`, `final_only`, `transitions_only`, and `full`. Existing `persist_state_snapshots=false` maps to `none`, while legacy `true` maps to `full`. Snapshot selection affects stored snapshots only. The default remains no per-row snapshots, and manifests/runtime summaries record the effective mode.

## Memory and budgets

Approximate memory includes input and normalized output DataFrames. Growth from 1,000 to 10,000 rows is approximately 10.00x. Highest measured 10,000-row path is Triple Screen Trading at 34.18 MB, followed by Pin Bar Rejection at 31.39 MB. These object-memory estimates exclude allocator fragmentation and shared library memory.

Aggregate budgets pass: overhead is below 3%, scaling below 12x, output variance zero, and repeated calculations zero. Six framework-specific overhead comparisons are warnings because separately sampled medians exceed 3%; five exceed the 5% hard-warning line, but none exceeds the 10% release-blocking tolerance. The aggregate paired architecture remains below target.

## Rejected optimizations

Blanket vectorization was rejected because state transitions and completed-bar dependencies are sequential. Global DataFrame, controller, session, or decision caches were rejected due to mutation and cross-run leakage risk. Setup/event ID formats were not changed because compatibility is more important than a small string-formatting gain. Existing diagnostics were not disabled by default, snapshots were not silently reduced, and validation/causality checks were not weakened.

Until chunked historical orchestration is explicitly designed, validated research runs should use at most 10,000 rows per framework invocation. A 50,000-row structural run was not included because the required 280-case, five-repetition matrix already consumed substantial local runtime; linear 1k/10k behavior provides the release evidence without producing large scratch traces.
