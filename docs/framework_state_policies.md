# Framework State Policies

## Research boundary and ownership

Phase 24.5 separates three responsibilities: frameworks propose completed-bar decisions, typed policies decide whether proposals are legal, and `ResearchStateController` applies the final research-state transition. Policies never place orders, model fills, access balances, or calculate profitability. Every rejection carries a stable `PolicyReasonCode`; descriptive text is supplementary.

## Generic lifecycles

Setups can be forming, armed, triggered, consumed, expired, or invalidated. Bar-count, timestamp, session-end, entry-cutoff, trend, level, and explicit framework invalidation are supported policy inputs. Expired, invalidated, and consumed setups cannot trigger again. Defaults retain the Phase 24.4 five-bar behavior and session-bound frameworks clear stale setup state at rollover.

An accepted exit may enter a configured cooldown. The controller exposes total and remaining bars and rejects entries with `COOLDOWN_ACTIVE`. Zero bars preserves legacy behavior. Optional maximum-hold enforcement uses elapsed bars or time and emits an advisory exit request with `MAX_HOLD_REACHED`; it does not simulate a fill or calculate a return.

Opposite signals support `ignore`, `reject`, `request_exit`, `exit_then_reverse`, and `allow_immediate_reverse`. The default is `request_exit`; a long-to-short or short-to-long transition cannot occur directly unless immediate reversal is explicitly enabled. Repeated exit requests and persistent same-side entries are suppressed.

## Framework-aware policies

- Opening Range requires sufficient completed opening data, exact range completion, an active entry window, one consumed breakout per session, and rollover cleanup. Opening state cannot carry into the next session.
- Inside Bar keeps an immutable mother-bar identity. Nested behavior is typed as keep original, replace latest, narrow range, or reject nested; keep original is the default. Structural violation, expiry, and one-shot consumption are explicit.
- RSI Pullback requires an armed threshold setup before a causal recovery crossing. Trend failure invalidates the setup, expiry is deterministic, and persistent recovery state cannot retrigger.
- Bollinger Squeeze progresses through squeeze active, release detected, breakout armed, triggered, and consumed. Minimum squeeze duration and maximum release-to-trigger age are configurable; squeeze re-entry can invalidate an armed release.
- Support/Resistance levels use stable IDs and candidate, confirmed, active, testing, bounced, broken, invalidated, and retired states. Only confirmed historical levels may be tested. Continuous-zone repeats, retest cooldown, structural break, maximum age, and optional cross-session carry are explicit. Role reversal is disabled by default.

Parabolic SAR, dual moving-average, MACD, ADX, SuperTrend, and breakout/pattern frameworks use event consumption: one flip or crossing yields one transition and persistent post-event state does not yield repeated entries. Controller instances are created per adapter run, so state cannot leak between runs.

## Session rollover

The session abstraction supports continuous 24/7, daily, and overnight boundaries with timezone-aware deterministic IDs. Rollover diagnostics include prior/new session IDs and cleanup actions. Untriggered and consumed session setups clear by default; cooldown clearing, position carry, session-close exit requests, and long-lived level carry are explicit choices. Missing first bars and skipped sessions are handled by comparing session IDs rather than assuming adjacent bars. No network calendar is required.

## Configuration, output, and manifests

New configuration fields cover expiration, three cooldown sources, maximum hold, opposite-signal mode, rollover choices, level retests, Inside Bar nesting, squeeze windows, and controller timing. Unknown fields and invalid enum/range combinations are rejected; old JSON configurations load with safe defaults.

Stateful rows append policy permission/reason, expiration/invalidation reasons, opposite action, cooldown, maximum hold, rollover actions, level diagnostics, and nanosecond timing. Existing normalized columns are unchanged. Manifests capture the policy and reason-code versions plus deterministic policy settings. Runtime timing is excluded from stable run identity.

## Instrumentation and validation

High-resolution monotonic timing independently records generic, setup, position, session, level, transition, serialization, and total controller categories. Disabled mode records zeros and avoids timer calls. Validators cover missing reason codes, illegal reversal, cooldown bypass, expired/consumed retriggers, stale session setup, premature level retests, future level use, illegal transitions, and nondeterminism. Causality tests modify only future inputs and compare policy/state output through the cutoff.

## Known limitations

Holiday calendars are not inferred, level discovery remains an upstream causal-data responsibility, and entries/exits remain advisory research state rather than fills. Timing varies by machine and is diagnostic only. Historical profitability evaluation, ranking, optimization, paper trading, and live execution remain out of scope.
