# Phase 25: deterministic SMC framework expansion

Phase 25 adds exactly fifteen Smart Money Concepts and ICT-style structural research frameworks to the existing B Trader framework library. The canonical library now contains exactly 50 frameworks and 50 validated framework configurations. Framework expansion is frozen at 50 after Phase 25. Future phases should focus on LLM-assisted research analysis rather than adding more frameworks.

## Shared causal contract

All fifteen frameworks use the existing registry, loader, normalized direct adapter, lifecycle controller, Phase 24.8 historical runner, and Phase 24.9 serial campaign planner. They read completed OHLCV bars and never mutate source frames. A symmetric swing with a right window of `n` bars becomes observable only when those `n` bars have closed. Its confirmation timestamp—not its pivot timestamp—is used for decisions. Higher-timeframe structure is backward-as-of aligned to the execution timeline.

Shared primitives provide confirmed swings, structural bias and breaks, raw-OHLC true range, displacement qualification, three-candle imbalance zones, zone fill lifecycle, equal-liquidity clustering, and confirmed dealing ranges. Typed `SMCFrameworkState` and `SMCZone` values round-trip through dictionaries, while normalized decision diagnostics carry lifecycle state, reason code, timestamps, zone bounds, and lineage.

## Framework definitions and distinctions

| Canonical ID | Deterministic definition | Principal lifecycle or distinction |
|---|---|---|
| `order_block` | Opposing candle zone qualified by a confirmed structure break and optional displacement | candidate, confirmed, active, touched, mitigated, invalidated, expired |
| `fair_value_gap` | Three-candle wick imbalance with an explicit minimum gap | detected, active, partially filled, filled, invalidated, expired |
| `break_of_structure` | Close- or wick-confirmed break of a previously confirmed swing | internal/external structural continuation event |
| `change_of_character` | Confirmed break against an established structural direction | requires prior bias, unlike BOS |
| `liquidity_sweep` | Temporary confirmed-swing violation followed by a close reclaim | distinct from a sustained breakout |
| `equal_high_low_liquidity` | Deduplicated confirmed-swing cluster within an explicit tolerance | activation and sweep/invalidation-ready pool identity |
| `breaker_block` | Failed structural zone transformed after opposing displacement | requires predecessor lineage; never independent |
| `mitigation_block` | Structural zone requiring a retracement through the relevant swing level | retracement requirement distinguishes it from order blocks |
| `premium_discount_zone` | Discount, equilibrium, or premium classification in a confirmed higher-timeframe dealing range | undefined until both range bounds are confirmed |
| `market_structure_shift` | Counter-bias structural break plus same-direction displacement | stricter than CHoCH |
| `balanced_price_range` | Price overlap of valid opposing imbalance zones | arbitrary consolidation is not sufficient |
| `displacement` | Completed candle meeting body/range, true-range multiple, and close-location thresholds | detected only at the completing bar |
| `judas_swing` | Session-window reference-range raid and reclaim | active, confirmed, expired |
| `kill_zone_setup` | Configured session window plus completed structural displacement | no execution behavior |
| `power_of_three` | Forward-only accumulation, manipulation, and distribution evidence | undefined, accumulation, manipulation, distribution, completed, invalidated, expired |

## Configuration

Every SMC framework exposes validated parameters for swing confirmation, close/wick break mode, zone age, imbalance size, true-range period and displacement thresholds, liquidity tolerance and touch count, reclaim window, zone boundary mode, session name/timezone/window, and bounded reference bars. Unknown parameters, invalid numeric ranges, identical session start/end times, invalid IANA timezones, and a displacement requirement with a zero true-range multiple are rejected.

`premium_discount_zone` uses `execution: 15m` and `structure: 1h`; the other fourteen defaults use `execution: 15m`. Session frameworks convert timezone-aware timestamps through the existing session abstraction, including overnight windows and daylight-saving transitions. No broker-local clock is assumed.

## Historical and campaign compatibility

The direct adapter remains the sole execution path. Dependency-aware warm-up covers confirmed swings and true-range periods. Historical chunks preserve the normalized controller state and produce the same stable output columns as continuous execution. Checkpoints, resume, recovery, integrity checks, merge validation, and completed-bar causality remain Phase 24.8 responsibilities.

`structural_all_50.json` is the current all-framework campaign configuration. Its `all` selector resolves the registry dynamically and campaign concurrency remains exactly one. `structural_all_35.json` is retained only as Phase 24.9 historical evidence; it is no longer the current primary campaign example.

## Research boundary

These modules classify deterministic structure and lifecycle evidence. They do not execute trades, download data, tune parameters, compare profitability, rank frameworks, or introduce a parallel registry, adapter, state system, or orchestration path.
