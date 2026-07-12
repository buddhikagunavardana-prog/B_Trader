# Phase 20.10A Performance Profiling Report

## Scope and baseline

The production fixed/generated research path was profiled against the existing
five-pair, 15-minute, approximately 365-day cached dataset. The Phase 20.9
generated-candidate stage baseline was 8,470.90 seconds for 200 strategy/pair
tasks and 78,071 persisted real trades. No strategy, indicator, signal,
backtest, scoring, robustness, or selection rule was changed.

## Production call chain

`benchmark_runner.run_full_benchmark` calls the research run manager and
production orchestrator. The fixed and generated adapters call
`generated_candidate_experiment`, which loads cached pair data, builds
strategy/pair tasks, and evaluates each task through `_run_backtest_grid`.
That function calculates indicators/signals once per strategy/pair and runs 16
SL/TP backtests. Each backtest calls `BacktestEngine.run`, then results are
scored and stage-level CSV/JSON artifacts are written. Orchestrator state is
updated at stage boundaries.

## Profile evidence

A one-candidate/one-pair production-path cProfile run took 122.23 seconds
under profiler overhead and made about 176.3 million calls. The backtest loop
accounted for 122.09 seconds. Pandas `iloc` row access accounted for 105.91
seconds cumulatively through 1,121,328 indexed reads; `fast_xs` alone used
74.97 cumulative seconds. Indicator calculation was not a material bottleneck.

After optimization, the same profiled workload took 6.87 seconds with
tracemalloc enabled, made about 3.0 million calls, and had a measured Python
allocation peak of 30.41 MiB. The remaining hot work is the mathematically
required per-candle backtest/equity loop and rounding. The combined profiler
made the pre-change memory run exceed five minutes, so a comparable pre-change
tracemalloc peak is unavailable and no memory-reduction claim is made.

## Repeated work and I/O findings

- Market data is loaded once per stage and shared with task workers. Fixed and
  generated stages independently read the same on-disk cache, but cache reads
  are negligible compared with the former backtest loop.
- Indicators and signals are calculated once per strategy/pair, then reused by
  all 16 SL/TP combinations. No duplicate indicator pass inside the grid was
  found, so no indicator cache was added.
- Two DataFrame copies exist per task, but profiling showed they were not a
  material hotspot.
- Trade artifacts are accumulated in memory and written once per stage. A
  6,953-row, 1.41 MB trade CSV took 0.034 seconds to write. Serialization and
  checkpoint I/O are not material bottlenecks.
- Candidate IDs are de-duplicated before execution; no duplicate task work was
  observed.

## Parallelism audit

The generic executor supports a Windows `ProcessPoolExecutor` with a default
safe ceiling of four workers, but production adapters currently force one
worker. On five candidates and one pair, runtimes were 2.814 seconds (one
worker), 2.481 seconds (two workers), and 2.319 seconds (four workers).
Canonical results were identical, but raw trade artifact order changed at four
workers because futures complete out of order. Production parallelism was
therefore left unchanged; a 1.21x gain does not justify changing deterministic
artifact ordering in this phase.

## Implemented optimization

`BacktestEngine.run` now takes read-only NumPy views of the existing close,
low, high, and signal columns once before the loop, while retaining the
original pandas index for timestamps. This removes per-candle pandas Series
construction. Candle order, stop-loss-before-take-profit evaluation, position
sizing, fees, equity updates, rounding, and trade allocation remain unchanged.
Input DataFrames and Series are not mutated.

## Performance results

| Workload | Before | After | Speedup |
|---|---:|---:|---:|
| 1 generated candidate × 1 pair | 37.242 s | 0.590 s | 63.16x |
| Full generated stage: 200 tasks | 8,470.902 s | 125.692 s | 67.39x |

The optimized small production path (10 fixed plus two generated strategies on
one pair) completed in 6.96 seconds. A five-candidate/five-pair workload
completed in 14.55 seconds, or 0.582 seconds per task.

## Equivalence and compatibility

The optimized full 200-row workload was compared with the completed Phase 20.9
artifacts. All non-runtime metrics, candidate/strategy IDs, pair/timeframe
values, scores, and all 78,071 trade records matched exactly. The small
benchmark also matched all 12 report rows and 4,215 trade records exactly.
Artifact schemas and candidate decisions are unchanged.

Existing resume/checkpoint tests pass. Because the optimization is
result-equivalent and does not alter schemas or contracts, completed artifacts
remain valid and no contract-version invalidation is required.

## Remaining bottlenecks and recommendation

The remaining generated-stage work is the necessary candle loop across 16
SL/TP combinations. Process parallelism could provide a small additional gain
after deterministic result ordering is explicitly designed and tested. The
current optimization already exceeds the 1.5x target without that risk.

Proceed to Phase 20.10B only after this change is reviewed; no full research
rerun is needed to establish equivalence because the complete prior artifacts
were compared exactly.
