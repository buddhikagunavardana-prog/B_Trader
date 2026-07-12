# Phase 20.11 — Progressive Research Funnel

The production orchestrator filters a single deterministic candidate cohort through
three calendar-based stages before optimization and the existing final validation
chain. No indicator, strategy, score, or final acceptance threshold is changed.

| Stage | Window | Partitions required to pass | Survivor artifact |
|---|---:|---|---|
| `funnel_3m` | 3 months | 2-month train + 1-month walk-forward | `funnel_3m_survivors` |
| `funnel_6m` | 6 months | 4-month train + 2-month walk-forward | `funnel_6m_survivors` |
| `funnel_1y` | 12 months | 8-month train + 2-month validation + 2-month final out-of-sample | `funnel_final_survivors` |

Each stage consumes only the previous survivor CSV and the immutable
`candidate_trades` artifact. Evaluation partitions must meet the configured early
funnel trade-count, profit-factor, and drawdown constraints. Training metrics are
recorded for audit but are not used as an out-of-sample acceptance substitute.

Every stage writes two versioned CSV artifacts: a PASS-only survivor handoff and a
complete audit containing PASS/REJECT status, rejection reasons, window boundaries,
and partition metrics. Candidate identity and all existing source/score columns are
preserved. Empty or insufficient evidence is rejected; it is never treated as a pass.

Resume uses the existing orchestrator state, config hash, artifact existence checks,
and per-stage contract version. A missing or incompatible artifact invalidates that
stage and causes it to run again. Legacy orchestrator configurations remain valid;
the robustness adapter falls back to the original candidate report when a final
funnel artifact is not present.
