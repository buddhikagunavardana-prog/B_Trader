# Phase 20.7 Production Benchmark Report

## 1. Repository State

- Branch: `main`
- Starting commit: `4cbe792ee0debe620261e46a836ebe3d5cfaf0b7`
- Comparison: local was 14 commits ahead of `origin/main` and 0 behind.
- Starting working tree: clean.
- Remote: `origin` points to `https://github.com/buddhikagunavardana-prog/B_Trader.git`.
- Local repository was treated as the source of truth. No pull, reset, checkout, restore, or push was performed.

## 2. Preflight Status

- Five-pair full preflight: `READY`.
- Production registry: 12 stages registered with production adapters; no smoke adapter was registered in the production registry.
- Imports: benchmark runner, production registry, and run manager imported successfully under Python 3.13.14.
- Dependency warning: `pytest` is not installed in the local virtual environment. The repository's directly executable test entry points were used instead.
- Final execution gate: `ARTIFACT_CONTRACT_FAILURE`. The Monte Carlo production adapter uses hard-coded integration returns rather than candidate trade artifacts. A full production benchmark was therefore not run.

## 3. Production Adapter Verification

The production registry contains `load_data`, `fixed_strategy_research`, `generated_candidate_research`, `optimization_search`, `parameter_optimization`, `walk_forward`, `market_regime`, `robustness_validation`, `portfolio_builder`, `monte_carlo`, `best_strategy_selection`, and `final_summary`.

Verified integration limitations:

- `monte_carlo_adapter.py` constructs `INTEGRATION_CANDIDATE` with fixed `trade_returns` and `trade_pnls`; its output is not evidence about an upstream researched candidate.
- `best_selector_adapter.py` deliberately calls `build_final_ranking([])` and produces an empty ranking instead of consuming upstream candidate metrics.
- `walk_forward_adapter.py` reports that detailed walk-forward remains delegated to the robustness engine.
- The small run's portfolio input was correctly empty because every generated candidate failed robustness.

## 4. Artifact Contract Verification

- JSON artifacts from the small run parsed successfully.
- All non-empty CSV artifacts parsed successfully.
- A genuine empty-result serialization bug was found: `portfolio_results.csv` had no header and could not be parsed by pandas.
- The portfolio report now writes the stable public candidate columns even when there are zero rows.
- Candidate IDs and optimizer hashes were deterministic in the inspected artifacts.
- The final ranking handoff is incomplete because no `final_candidate_metrics` or `benchmark_candidate_metrics` artifact is produced.
- The Monte Carlo input contract is incomplete because upstream per-candidate trade returns/PnLs are not carried into the adapter.
- No formulas, thresholds, or strategy logic were changed.

## 5. Data Coverage Summary

All files are under `data/cache/binance/`; no network download was required.

| Pair | Timeframe | Earliest | Latest | Candles | Missing | Duplicates | Invalid | Cache file |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BTCUSDT | 15m | 2025-07-09 13:15 | 2026-07-09 13:00 | 35,040 | 0 | 0 | 0 | `btcusdt_15m_1_year_ago_utc_none.csv` |
| ETHUSDT | 15m | 2025-07-09 13:15 | 2026-07-09 13:00 | 35,040 | 0 | 0 | 0 | `ethusdt_15m_1_year_ago_utc_none.csv` |
| BNBUSDT | 15m | 2025-07-09 13:15 | 2026-07-09 13:15 | 35,041 | 0 | 0 | 0 | `bnbusdt_15m_1_year_ago_utc_none.csv` |
| SOLUSDT | 15m | 2025-07-09 13:30 | 2026-07-09 13:15 | 35,040 | 0 | 0 | 0 | `solusdt_15m_1_year_ago_utc_none.csv` |
| XRPUSDT | 15m | 2025-07-09 13:30 | 2026-07-09 13:15 | 35,040 | 0 | 0 | 0 | `xrpusdt_15m_1_year_ago_utc_none.csv` |

Actual coverage is approximately one year, not ten years.

## 6-13. Small Benchmark Stage Summary

- Run ID: `phase_20_7_small_benchmark`
- Mode: supported `SMALL_BENCHMARK` profile (BTCUSDT/15m, maximum cached history).
- Exit status: 0.
- Orchestrator status: `COMPLETED`; 12 completed, 0 failed, 0 blocked.
- Fixed strategy adapter output: 2 rows. The generated-candidate experiment separately evaluated 10 fixed definitions and 2 generated strategies across 12 tasks.
- Optimization search: 3 candidates selected; candidate CSV and search metadata were readable.
- Parameter optimization: 3 rows normalized as `SELECTED_FOR_EVALUATION`.
- Walk forward: 2 rows; detailed validation was delegated to robustness.
- Market regime: 1 BTCUSDT row.
- Robustness: 2 evaluated, 0 accepted.
- Portfolio: 0 inputs, 0 allocations; allocation invalid because no candidate passed robustness.
- Monte Carlo: 20 simulations completed, but the result is invalid for production ranking because the adapter used hard-coded integration returns.
- Final selection: 0 ranking rows by adapter design; the top-level shortlist object contained no ready or promising candidates.

## 14-17. Ranking, Readiness, and Rejections

No valid final ranking or paper-trading-ready candidate was produced.

| Candidate / Strategy ID | Pair | Trades | ROI | Profit Factor | Win Rate | Max Drawdown | Walk-forward pass | Walk-forward score | Robustness | Status | Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `BRK001_EMA20_100_ATR14_SL1P5_TP3P0` | BTCUSDT | 374 | -13.64% | 0.95 | 32.35% | -25.08% | 50% | 64.62 | 42.97 | REJECTED | Profit factor below minimum; pair consistency weak |
| `BRK001_EMA20_100_ATR14_SL1P5_TP4P0` | BTCUSDT | 374 | -13.64% | 0.95 | 32.35% | -25.08% | 50% | 64.62 | 39.82 | REJECTED | Profit factor below minimum; pair consistency weak |

Monte Carlo results and final scores are intentionally omitted for these candidates because the Monte Carlo artifact was not candidate-derived.

## 18-20. Warnings and Runtime

- The small run took 427.55 seconds end to end.
- The first fixed-strategy adapter stage took 92.99 seconds.
- The generated-candidate experiment reported 264.68 seconds for its fixed set and 54.19 seconds for generated strategies.
- Exact independent runtimes for later stages are unavailable after the resume run replaced their stage-result entries with resumed `SKIPPED` records; no values were fabricated.

## 21. Artifacts Created

The small-run directory contains coverage and market manifests, fixed/generated reports, optimizer candidates and metadata, parameter optimization, walk-forward, market-regime, robustness report and shortlist, portfolio results and metrics, Monte Carlo results and summary, final ranking/shortlist/rejections, orchestrator state/summary/stage report, run manifest/summary, config snapshots, and reproducibility summaries.

## 22. Resume Status

- Checkpoint: `reports/research_runs/phase_20_7_small_benchmark/orchestrator_state.json`
- Completed before resume: all 12 stages.
- Resume invocation runtime: 0.25 seconds.
- Resumed stage behavior: every completed stage was marked `SKIPPED` with `Resumed completed stage` and `metadata.resume=true`.
- Previous artifacts reused: yes.
- Resume validation: passed with 12 skipped, 0 failed.

## 23. Paper Trading Readiness Decision

`NOT READY`. The researched generated candidates failed existing robustness requirements, and the production Monte Carlo/final-selection artifact chain is not connected to real candidate trade outputs. Phase 21.0 should not begin from this run.

## 24. Bugs Found

1. Fixed: empty portfolio reports were headerless and unreadable (`ARTIFACT_CONTRACT_FAILURE`).
2. Open: Monte Carlo uses hard-coded integration data rather than upstream candidate trades (`ARTIFACT_CONTRACT_FAILURE`).
3. Open: best-strategy selection always receives an empty candidate list (`ARTIFACT_CONTRACT_FAILURE`).
4. Open limitation: standalone walk-forward adapter delegates detailed validation to robustness.

## 25. Files Changed

- `src/research/portfolio/portfolio_report.py`
- `src/tests/test_portfolio_foundation.py`
- `docs/phase_20_7_production_benchmark_report.md`

Relevant direct tests passed: full benchmark contract tests, production adapter tests, research orchestrator tests, research run-management tests, and portfolio foundation tests. Full benchmark execution was correctly withheld after the artifact-contract gate failed.
