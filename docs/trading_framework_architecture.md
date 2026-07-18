# Trading Framework Architecture

## Purpose and boundary

Phase 24.1 introduces a reusable decision layer between precomputed indicators and downstream risk/execution engines. An indicator calculates market information. A strategy remains the repository's configurable rule configuration. A trading framework is a named, typed interpretation of indicators, timeframe roles, entries, exits, and proposed risk controls. A framework never downloads data, resamples bars, calls an exchange, places an order, or claims profitability.

```text
Market data -> Indicator engine -> Trading framework -> Decision
                                                    -> Risk engine -> Backtest/paper/live execution
```

## Lifecycle and execution contract

1. The caller prepares one DataFrame per required timeframe role and computes indicator columns outside the framework.
2. `load_framework(name, parameters)` resolves a canonical name or alias and validates overrides.
3. `FrameworkContext` supplies the explicit role mapping, current position, and optional symbol.
4. `execute(context, timestamp)` validates roles, `DatetimeIndex` ordering, duplicate timestamps, and required columns.
5. Every frame is sliced to rows whose completed-bar close timestamp is at or before the decision timestamp.
6. The implementation returns one immutable `FrameworkDecision`. Repeated calls with the same inputs produce the same output and do not mutate source frames.

Indexes represent candle closing times. A higher-timeframe row is visible only after that timestamp. If a data source labels candles by open time, the preparation layer must convert them to close/availability timestamps. Frameworks do not resample and never reconstruct unfinished candles.

```python
from src.trading_frameworks import FrameworkContext
from src.trading_frameworks.loader import load_framework

framework = load_framework("triple_screen", {"risk_fraction": 0.005})
decision = framework.execute(FrameworkContext({
    "trend": completed_1h,
    "setup": completed_15m,
    "entry": completed_5m,
}))
```

## Domain schema

`FrameworkMetadata` covers identity, version, attribution, stability, markets, directions, timeframes, indicator dependencies, data requirements, regime compatibility, tags, aliases, and reference notes. `ParameterDefinition` supports integer, float, boolean, string, enum, timeframe, percentage, period, and optional values, with bounds, allowed values, descriptions, and optimization eligibility.

`FrameworkSchema` combines metadata with role-specific columns, parameter definitions, entry/exit/risk/trade-management descriptions, and the causal contract. `to_dict()` produces a GUI-safe structure. A later JSON adapter can populate the same schema without changing runtime consumers.

## Decision and risk contracts

Signals are `BUY`, `SELL`, `EXIT_LONG`, `EXIT_SHORT`, `HOLD`, or `NO_TRADE`. A decision includes direction, confidence, entry/exit flags and reasons, active timeframe, timestamp, framework identity/version, diagnostics, warnings, and a `RiskProposal`. It cannot contain an exchange order.

Risk proposals are advisory. They can describe stop and target types/levels, stop distance, reward-to-risk, ATR volatility unit, trailing-stop type, risk fraction, maximum holding period, sizing hint, and scale-in/scale-out hints. The Phase 24.1 reference implementations use `atr_multiple` stops and `reward_multiple` targets. The risk engine remains responsible for account-aware sizing and execution approval. The model is extensible to fixed percentage, indicator level, channel level, swing level, time stop, and no-stop proposals.

## Registry, loader, and validation

`trading_framework_registry` owns five canonical classes. Aliases resolve to a canonical name but do not increase inventory. Duplicate names/aliases and invalid categories fail during registration. Registry entries are serializable and can be filtered by category, market, timeframe, or stable status.

The loader instantiates a fresh reusable framework, merges defaults with overrides, and rejects unknown names, parameters, invalid types, non-finite values, and range violations. `load_framework_metadata()` supports discovery without execution.

The validator returns structured `ERROR`, `WARNING`, and `INFO` issues. Release validation checks metadata, categories, roles, indicator-registry dependencies, parameter documentation/uniqueness/defaults, deterministic outputs, finite values, non-mutation, and future-row causality. Documentation and inventory are release artifacts rather than console-only output.

## Adding a framework

1. Add a category module implementing `BaseTradingFramework` with immutable metadata and a complete `FrameworkSchema`.
2. Declare every role and required precomputed column. Resolve indicator dependencies by canonical indicator-registry name.
3. Implement `generate_decision()` using only the causally sliced context. Cast diagnostic numeric values to ordinary Python numbers.
4. Register the class in `_register_defaults()` and add reference, edge-case, non-mutation, causality, and timing tests.
5. Regenerate the inventory, run registry/runtime validation, and update the library guide. Do not embed data access, resampling, global state, network calls, or execution code.

## Phase 24.1 limitations and future integration

This release provides architecture and deterministic reference logic, not validated trading performance. It does not include historical research, optimization, walk-forward analysis, ranking, portfolio pyramiding, maximum-hold enforcement, order execution, exchange connectivity, AI generation, or a GUI. Scale-in and holding-period values are metadata hints only.

A future GUI can consume registry/schema dictionaries for framework discovery and safe parameter controls. A future research pipeline can supply precomputed frames, record immutable decisions, route risk proposals through the risk engine, and compare frameworks without changing their execution contract.

Phase 24.3 expands the same contract to twenty canonical frameworks and adds `momentum` and `price_action` categories. Similar event frameworks share a rule engine, but each remains an explicit registry class with its own schema, metadata, dependencies, parameters, source module, and example configuration. Event signals represent transitions; persistent states must not emit repeated entries.
