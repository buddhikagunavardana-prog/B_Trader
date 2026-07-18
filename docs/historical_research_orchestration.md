# Resumable Historical Research Orchestration

Phase 24.8 adds deterministic, bounded, resumable execution for the existing
framework research adapter. It does not add trading or profitability analysis.

## Public API

The supported entry points are exported by
`src.research.frameworks.historical`:

- `HistoricalResearchRunConfig` defines an immutable run contract.
- `plan_historical_run(config, sources)` creates deterministic row-based chunks.
- `run_historical_research(plan, sources)` executes one bounded chunk at a time.
- `resume_historical_research(run_directory, sources)` validates and resumes a run.
- `validate_historical_run(run_directory)` validates every durable chunk.
- `merge_historical_artifacts(run_directory)` creates a deterministic merged CSV.

All imports use the repository-root `src.` namespace.

## Planning and sources

Run identity covers the framework configuration, requested timestamp range,
chunk and overlap policy, integrity controls, memory limit, artifact contract,
and fingerprints for every source role. Chunk identities and predecessor links
are deterministic. Logical output ranges are disjoint and exhaustive.

`InMemoryDataFrameSource` supports already-loaded frames. `LocalCsvSource`
retains only timestamp-index metadata and uses bounded `skiprows`/`nrows` reads
for each chunk. Optional Parquet reads require a pandas Parquet engine already
installed by the operator. Every source rejects non-monotonic or duplicate
timestamps. Multi-timeframe reads end at the current execution chunk's last
timestamp, preserving completed-bar alignment.

Dependency-aware overlap is the default. The planner combines explicit warm-up,
framework minimum history, parameter periods, multi-timeframe needs, and
session-aware floors. Fixed-row and no-overlap policies are also available.

## Execution and continuity

Only one chunk is materialized and processed at a time. Before execution, input
memory is measured against `maximum_memory_bytes`; the run fails closed when the
strict target is exceeded. Artifact row counts are bounded independently.

Stateful runs persist explicit JSON-compatible position, setup, session, and
event-continuity state. Every checkpoint records both the predecessor state
fingerprint and the next chunk's initial-state fingerprint. This makes a broken
continuity chain detectable and forces invalidation from its earliest bad chunk.

Cancellation is checked at safe chunk boundaries. A cancelled run retains only
fully written, validated chunks and can be resumed.

## Durable files and atomicity

Each run contains:

```text
<run-id>/
  plan.json
  manifest.json
  chunks/chunk_000000/
    decisions.csv.gz
    checkpoint.json
  merge_manifest.json
  merged_decisions.csv
```

JSON, decision artifacts, checkpoints, and manifests are written to temporary
files, flushed, and atomically replaced. A decision artifact is durable before
its checkpoint. Therefore an artifact without a checkpoint is never accepted as
complete. Checksums, schema fingerprints, configuration fingerprints, code
fingerprints, source fingerprints, row counts, timestamp order, logical ranges,
and predecessor state are validated before reuse or merge.

Chunk locks use exclusive creation and a bounded stale timeout. Recovery removes
orphan temporary files and moves invalid chunk directories under `superseded/`
instead of treating them as valid output.

## Recovery procedure

1. Recreate the exact source bundle.
2. Call `validate_historical_run(run_directory, strict=False)` to inspect damage.
3. Call `resume_historical_research(run_directory, sources)`.
4. The recovery scan retains the longest valid prefix and invalidates every
   downstream chunk from the first continuity break.
5. After completion, call `merge_historical_artifacts(run_directory)`.

Resume rejects changed sources, configuration, code, schema, checkpoint version,
or predecessor state. A stale manifest does not discard valid checkpoints; the
durable checkpoint chain is authoritative. Gaps, overlaps, and out-of-order
stored plans are rejected before execution or merge.

## Runtime safety

Historical run directories, chunk runtime directories, temporary files, locks,
recovery patches, traces, caches, raw cached market data, and environment files
are excluded from Git. Operators should keep credentials and raw market data
outside the repository.

## Scope exclusions

Phase 24.8 contains no PnL, ROI, win rate, profit factor, drawdown, Sharpe ratio,
framework ranking, parameter optimization, profitability walk-forward, portfolio
or fill simulation, paper trading, live trading, broker or exchange API, AI
execution, GUI, new indicator, or new framework behavior.
