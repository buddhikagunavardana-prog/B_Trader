# Top 150 Indicator Library Validation

## Release decision

The Phase 23.5 deterministic release gate classifies the 150-indicator library
as **research-ready**. The registry contains 138 stable and 12 experimental
entries. No unresolved critical or high-severity defect remains. Experimental
tools are safe for controlled research but are excluded from default strategy
generation unless a researcher opts in explicitly.

This decision covers deterministic research infrastructure only. It is not a
claim of trading profitability and does not authorize paper, live, exchange,
optimization, walk-forward, or full historical research workflows.

## Validation coverage

The release gate checked all 150 canonical entries for callable and source
validity, registry metadata, dependencies, output metadata, input index
alignment, non-mutation, missing-column errors, parameter errors, finite output,
causality, collision status, and engine compatibility. Inventory numbering is
exactly 1 through 150 and aliases are not primary entries.

Independent exact formula fixtures cover 31 representative tools. Another 35
were compared with published/reference definitions encoded in repository
source and deterministic tests. Remaining tools received source derivation
review plus category-level numerical fixtures and complete runtime contracts.
Floating comparisons use `rtol=1e-12` and `atol=1e-12` for causality; exact
pandas equality is used when the formula path is identical.

Input contracts were exercised with normal synthetic data, constant price,
monotonic up and down trends, gap-heavy data, zero volume, sparse NaNs, three-row
inputs, large finite values, and small decimal values. Duplicate indexes and
unsorted indexes are accepted and preserved positionally. Indicators assume
rows are already in chronological order, so callers must sort before research;
the registry does not silently reorder market data.

## Causality audit

Every canonical indicator passed a dynamic future-change test: candles after a
fixed cutoff were changed and outputs through the cutoff remained identical.
The source tree also passed AST checks for centered rolling windows, negative
shifts, and backward filling.

Ichimoku components are aligned to when values are available. Its cloud spans
use positive displacement, and its lagging series is trade-safe rather than a
traditional backward-plotted visualization. Swing, fractal, equal-high/low,
and sweep outputs occur only after their right-side confirmation delay. FVG,
inverse FVG, order block, breaker block, BOS/CHoCH, and liquidity sweep are
event outputs; downstream code must explicitly manage any persistent zones.

## Output and implementation audit

The registry declares 254 output columns with no duplicate canonical owners.
Running all nonlegacy indicators through the engine produces no duplicate
DataFrame columns and exposes every declared output.

Phase 23.5 found and fixed two high-severity engine mapping defects. First,
`fibonacci_retracement` returned correctly standardized Series names, but the
engine attached dictionary keys as undocumented columns such as
`FIBONACCI_RETRACEMENT_23.6`. The engine now honors each standardized Series
name, including `FIBONACCI_23_6`, without changing attachment architecture.
Second, generic aliases are resolved to their canonical registration before
engine mapping, and configuring both an alias and its canonical name now raises
a clear error rather than silently overwriting output columns. This also keeps
multi-output alias mappings complete.

Three unregistered functions remain intentionally outside the canonical list:

- `calculate_breakout_levels` is a backward-compatible helper beside the
  registered causal breakout detector.
- `calculate_fibonacci_levels` is a legacy scalar helper superseded by the
  registered rolling DataFrame implementation.
- `calculate_aroon_oscillator` is an unused standalone derived view; Aroon Up
  and Down remain the canonical registration.

They are currently unreachable from the registry and strategy definitions.
Removal can be considered in a dedicated cleanup phase after compatibility
review.

## Experimental indicator decisions

All 12 retain experimental status and should be disabled by default.

| Indicator | Definition and defaults | Confirmation | Limits and expected failures | Research use |
|---|---|---|---|---|
| Jurik MA approximation | Volatility-adaptive recursive smoother; period 14, phase 0, power 2 | Current candle after warm-up | Not proprietary JMA; parameter sensitivity | Exploratory smoothing only; do not claim JMA equivalence |
| Ehlers Super Smoother | Approximate causal two-pole filter; period 10 | Current candle after seeded warm-up | Seed and coefficient convention vary | Cycle/noise research; exclude from default generation |
| Ehlers Roofing Filter | Approximate high-pass 48 plus smoothing 10 | Current candle after warm-up | Approximation and edge transients | Exploratory detrending; not a spectral estimator |
| Cycle Identifier | Half-period lag autocorrelation; period 20 | Current candle after two windows | Harmonics, trends, and regime shifts can mislead | Feature research only; not a dominant-cycle claim |
| Fair Value Gap | Three-candle gap against candle t-2 | Event on candle t | Does not persist or model fills | Pattern research; not institutional-flow detection |
| Order Block | Previous opposite candle plus prior-range breakout; period 20 | Breakout candle, one candle after candidate | Heuristic candidates and sparse events | Controlled price-action research only |
| Market Structure | Close break of prior rolling extremes; period 20 | Break candle | Range rule approximates BOS/CHoCH | Regime/event feature; not institutional structure truth |
| Inverse FVG | Close through latest opposing confirmed FVG | Invalidation candle | Tracks only latest gap per direction | Event research; downstream persistence required |
| Liquidity Sweep | Wick rejection of latest confirmed swing; period 5 | Sweep candle after swing was confirmed | Misses hidden liquidity and is tolerance-free | Rejection-pattern research only |
| Equal Highs | Confirmed swing comparison; period 5, tolerance 0.001 | Five-candle right-side delay | Sensitive to scale and tolerance | Structure clustering research |
| Equal Lows | Confirmed swing comparison; period 5, tolerance 0.001 | Five-candle right-side delay | Sensitive to scale and tolerance | Structure clustering research |
| Breaker Block | Order-block invalidation with matching BOS/CHoCH; period 20 | Invalidation/structure candle | Compounds two heuristic approximations | Controlled event research only |

## Dependency and redundancy review

Dependency metadata is complete and valid. Existing local reuse includes ATR,
RSI, EMA, Bollinger, Keltner, Donchian, directional movement, swing, FVG,
order-block, and market-structure families. No global cache was added.

Conceptual redundancy should be controlled during later strategy search:

- DMI, Plus DI, and Minus DI share directional calculations but expose useful
  paired and standalone contracts.
- Historical Volatility and Close-to-Close Volatility share log-return
  variance; the former reports percent units and the latter decimal units.
- DEMA/TEMA are lag-reduced combinations, while Double-/Triple-Smoothed EMA
  are sequential smoothers and are not formula duplicates.
- LSMA and Z-Score aliases map to existing canonical entries and are not
  counted separately.
- ATR, Bollinger, Keltner, Donchian, moving-channel, volume-flow, and structure
  families may be highly correlated. Later search should cap same-family
  feature selection rather than remove canonical tools.

## Performance and memory

The deterministic benchmark uses one warm-up and three measured full-library
runs per size. Approximate memory is the retained working-set increase sampled
after full-library repetitions; short transient peaks can be higher.

| Rows | Runs (seconds) | Average | Per indicator | Approx. memory increase |
|---:|---|---:|---:|---:|
| 1,000 | 0.241600, 0.219828, 0.236717 | 0.232715 | 0.001551 | 1.902 MiB |
| 10,000 | 0.999951, 0.970789, 0.961253 | 0.977331 | 0.006516 | 0.000 MiB retained |
| 50,000 | 4.601248, 4.497895, 4.461829 | 4.520324 | 0.030135 | 0.719 MiB |

The 10,000-row average is 44.1% below the Phase 23.4 snapshot of 1.748 seconds;
machine and allocator state make this a smoke comparison rather than a formal
microbenchmark. Scaling is 4.20x from 1,000 to 10,000 rows and 4.63x from
10,000 to 50,000 rows, with no suspicious aggregate superlinear behavior.
Detailed slowest-ten results are in the performance CSV.

The engine still attaches columns one at a time and emits pandas fragmentation
warnings. This is retained technical debt because batching could change public
mutation and sequential custom-source behavior.

## Defect classification

- Critical: none found.
- High: two engine defects—Fibonacci dictionary naming and alias/canonical
  silent overwrite—fixed and regression-tested.
- Medium: none unresolved.
- Low: Klinger emitted a divide warning on zero-range flat data; fixed with
  explicit safe division. Unregistered legacy helpers and engine fragmentation
  remain documented warnings.

## Release gate evidence

The release gate passes: exactly 150 unique canonical entries, no stable
look-ahead failure, no stable deterministic execution failure, valid source and
metadata, no unexplained collisions, passing downstream synthetic strategy
tests, and explicit experimental labeling. Full strategy research remains a
separate future phase.

## Executed and skipped suites

Executed deterministic suites: indicator library validation, indicator
framework, registry, engine, expansion, strategy templates, professional
strategies, market regime, backtest-performance helpers, and the small
synthetic backtest.

Intentionally skipped network or exchange-data suites:
`test_download_data`, `test_signal_engine`, `test_real_backtest`,
`test_multi_pair`, and `test_simple_optimizer`. They download Binance data,
exercise exchange-connected paths, run multi-pair history, or combine those
operations with optimization.

Intentionally skipped optimization and broad research suites:
`test_full_benchmark`, `test_system`, `test_optimizer_foundation`,
`test_optimizer_search`, `test_parameter_generator`, `test_parameter_manager`,
`test_generated_candidate_experiment`, `test_generated_strategy_robustness`,
`test_monte_carlo_foundation`, `test_portfolio_foundation`,
`test_production_adapters`, `test_progressive_funnel`,
`test_research_orchestrator`, `test_research_pipeline`, and
`test_research_run_management`. These are outside the validation-only phase;
`test_system` also invokes the optimizer.

Intentionally skipped AI suites: `test_ai_research` and
`test_strategy_proposals`. Even though mock paths exist, Phase 23.5 expressly
excludes AI analysis and proposal generation.
