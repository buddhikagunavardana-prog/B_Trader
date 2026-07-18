# Framework Research State

## Phase 24.6 framework integration

The policy registry now recognizes the ten new setup-bearing frameworks and all fifteen new event frameworks. Pivot Range is session-bound; Pin Bar is level-bound. Every adapter run creates fresh state, setup expiry and consumption suppress retriggers, opposite events use the configured Phase 24.5 mode, and daily pivot levels clear on rollover.

## Phase 24.5 policy enforcement

The controller now evaluates typed setup, position, session, level, opposite-signal, event-consumption, cooldown, and maximum-hold policies before applying transitions. Machine-readable reason codes make every accepted or rejected proposal observable. Session rollover clears configured state deterministically, while framework-aware policies define Opening Range, Inside Bar, RSI Pullback, Bollinger Squeeze, and Support/Resistance behavior. Controller timing is opt-in runtime metadata and never affects deterministic run IDs. See `framework_state_policies.md` for the full contract.

Phase 24.4 adds deterministic research memory without execution simulation. `ResearchStateController` owns serializable position, setup, and session state; frameworks remain stateless and cannot mutate it. Position states cover flat, pending, active long/short, exit pending, and cooldown. Conservative defaults allow one advisory position, suppress repeated entries, disable automatic reversal, and return directly to flat on the matching exit request. Quantities, fills, balances, fees, and PnL are absent.

Setup states cover none, forming, armed, triggered, expired, invalidated, and consumed. Inside Bar, Opening Range, RSI Pullback, Support/Resistance, and Bollinger Squeeze receive setup IDs, ages, transitions, consumption, and expiry diagnostics. Sessions support 24/7, recurring daily, and overnight definitions with timezone, opening range, cutoff, weekdays, stable IDs, and optional future holiday-provider boundaries without network dependencies.

`IndicatorRequest` defines canonical indicator, validated parameters, output alias, and stable fingerprint. Explicit `COMPUTE_MISSING` supports EMA 8/13/21/34/55 and dual-average variants, rejects duplicate/colliding aliases, deduplicates fingerprints, and records provenance. `PRECOMPUTED_ONLY` remains default.

Stateful output appends position/setup/session transitions, ages, IDs, opening-range completion, warnings, and validity while retaining every existing normalized column. Manifests snapshot policy, sessions, setup expiry, provenance, initial state, and runtime final-state summary without embedding decisions. This is research context, never broker or profitability state.
## Runtime snapshot policy

Snapshot storage supports `none`, `final_only`, `transitions_only`, and `full`. Legacy `false`/`true` values map to `none`/`full`; the default therefore remains backward compatible. Snapshot selection never changes controller transitions or normalized decisions.
