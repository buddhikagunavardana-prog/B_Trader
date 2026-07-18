# Deterministic historical research campaigns

Phase 24.9 adds a thin campaign coordinator above the Phase 24.8 historical-run engine. A campaign expands registry-selected framework configurations, named local source sets, and explicit research ranges into independent child runs. It does not execute chunks itself.

## Responsibility boundary

The campaign layer owns deterministic matrix expansion, serial child scheduling, campaign manifests, campaign locking, child reuse, campaign recovery assessment, and structural summaries. Phase 24.8 continues to own bounded source reads, warm-up overlap, completed-bar alignment, framework execution, continuity state, child checkpoints, child artifacts, child locks, resume, validation, and merge.

The general research DAG and generic run registry are unchanged.

## Deterministic planning and identities

`plan_historical_campaign` resolves framework configurations through `trading_framework_registry`, validates named runtime source-set bindings, and calls `plan_historical_run` for every compatible child. Framework selection may use canonical names or the `all` selector. The planner never assumes that the registry contains 35 entries, so a future registry expansion does not require campaign redesign.

Campaign and task identities use canonical configuration values, framework configuration fingerprints, source and schema fingerprints, research bounds, schema versions, and code fingerprints. Mapping insertion order does not affect an identity. Current time, elapsed time, host, user, process, random UUIDs, absolute source locations, and temporary paths are excluded.

Row ranges use a zero-based inclusive start and exclusive end. They are resolved to the primary source index before the Phase 24.8 child plan is created. Timestamp ranges preserve Phase 24.8's inclusive timestamp semantics.

Planning is side-effect free: it may validate source indexes and bounded planning metadata, but it creates no campaign or child runtime directory.

## Named local source sets

Runtime code supplies `HistoricalSourceSetBinding` objects. Each binding declares a safe name, role-to-timeframe mapping, execution timeframe, compatible framework names, and Phase 24.8 sources. A binding fingerprint excludes source locations while including content, schema, index coverage, and timeframe metadata.

Source bindings are explicit and local. Campaigns do not download data, invoke exchanges, mutate source files, or infer missing higher-timeframe data. Multi-timeframe roles must be provided and continue to use Phase 24.8 completed-bar alignment.

Portable configuration files contain only source-set names. Local source paths belong in ignored runtime binding configuration, never in committed campaign configuration.

## Serial bounded execution

`run_historical_campaign` accepts only `concurrency=1`. For each task it resolves one child, calls Phase 24.8 planning, reuses or resumes the child, validates it, merges it, extracts bounded structural metadata one chunk at a time, releases the chunk frame, and advances. It never retains all child frames, merged outputs, snapshots, or decisions in memory.

Cancellation and pause are checked before and after every child and before summary creation. Cancellation inside a child is delegated to Phase 24.8. A safe stop preserves every previously validated child and permits later resume.

## Runtime layout

```text
<output_root>/<campaign_id>/
    campaign_plan.json
    campaign_manifest.json
    campaign_status.json
    campaign_integrity.json
    campaign.lock
    task_results/<task_id>.json
    summaries/structural_summary.csv
    summaries/structural_summary_manifest.json
    children/<child_run_id>/
```

Campaign IDs, task IDs, and resolved paths are validated against traversal and separator injection. JSON and CSV metadata use temporary writes followed by atomic replacement. A campaign-level lock coordinates the campaign; Phase 24.8 child locks retain responsibility for child execution.

## Resume and recovery

Resume checks campaign schema, identity, plan ordering, source-set fingerprints, framework configuration fingerprints, code fingerprints, task results, child validation, child integrity fingerprints, and aggregate integrity. Valid independent children are retained. An invalid task does not invalidate unrelated children, but every summary containing it becomes stale and must be regenerated.

Recovery assessment reports retained, reused, resumed, invalidated, and rerun tasks; orphan or corrupt files; incompatible files; stale summaries; and retained child runs. Phase 24.8 performs any required chunk-level invalidation and recovery within a child.

## Structural summaries

Only integrity-valid child runs enter a summary. Allowed evidence includes identities, statuses, row and chunk counts, valid and skipped counts, normalized direction and lifecycle-state counts, warnings, validation counts, schemas, fingerprints, and explicitly diagnostic memory or elapsed-time observations.

Financial outcomes, profitability metrics, framework scores, ranks, winners, best-framework fields, and recommendations are forbidden. Schema guards reject prohibited field names. Summary ordering follows the deterministic campaign task order, never an outcome measure.

## Portable examples

- `structural_smoke.json` selects representative stateless, stateful, session-aware, daily, and multi-timeframe frameworks.
- `structural_all_50.json` is the current primary configuration and selects the registry through `all`; the exact count is validated by release tests rather than embedded in campaign internals.
- `structural_all_35.json` is retained as historical Phase 24.9 evidence and is not the current primary configuration.

Both require separately supplied local source bindings and perform no network access.
