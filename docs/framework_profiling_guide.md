# Framework Profiling Guide

Phase 24.7 profiling is deterministic, synthetic, network-free, and separate from profitability research. The profiling package records total, preparation, alignment, framework decision, controller, policy, session, setup, position, diagnostics, normalization, serialization, and manifest time plus approximate DataFrame memory.

Use `profile_framework` for a focused framework and `profile_matrix` for the checkpointed release matrix. Release measurements use one warm-up and five measured runs at 1,000 and 10,000 rows for stateless, stateful, stateful-policy, and instrumented stateful-policy modes. Reports retain mean, median, minimum, maximum, population standard deviation, and p90. Medians drive budgets.

The stateful and stateful-policy labels exercise the same controller-owned policy architecture in this release; both are retained to expose the requested mode boundary without inventing an unsafe policy bypass. Instrumented mode adds high-resolution monotonic component timers. Normal adapter runs do not enable them.

Checkpoints contain aggregate measurements only, not raw traces or decision rows. A complete matrix has 280 unique framework/row-count/mode records, five measured runs, one warm-up, and zero repeated indicator calculations. Delete incomplete scratch traces rather than committing them; the canonical summary CSV is a release report.

Budget interpretation:

- Aggregate instrumentation target: below 3%; per-framework 3–5% is a warning, above 5% a hard warning, and above 10% release-blocking.
- Scaling target: approximately 10x for 10x rows; above 12x is release-blocking pending investigation.
- Repeated indicator calculation count: exactly zero.
- Memory growth: approximately linear; above 12x is a warning.
- Output variance: zero outside instrumentation timing fields and intentionally selected diagnostic payload detail.

Profiling reports are structural evidence only. They must not contain PnL, ROI, win rate, Sharpe ratio, drawdown, profitability ranking, fills, or exchange execution data.
