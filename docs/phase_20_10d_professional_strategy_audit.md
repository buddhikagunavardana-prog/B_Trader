# Phase 20.10D Professional Strategy Portfolio Audit

## Execution paths

Single-pair definitions load through `json_strategy_loader`, are materialized by
`strategy_factory`, receive registered indicators in `indicator_engine`, and
dispatch through `PROFESSIONAL_STRATEGY_SIGNALS` in `signal_engine`. The output
is an index-aligned BUY/HOLD Series consumed by the unchanged long-only
`BacktestEngine`; stage reports and candidate trades are produced by the
existing research adapters.

Cross-sectional rotation enters through
`research.portfolio.relative_strength_overlay`, consumes synchronized pair
DataFrames, calls `rank_relative_strength`, and returns Pair, Score, Weight,
and Rank columns. It is excluded from single-pair candidate templates.

## Correctness and formula audit

- Time-series momentum requires close above EMA96, EMA32 above EMA96, positive
  eight-bar EMA96 slope, ADX >= 18, and close above the shifted 20-bar Donchian
  upper level. Warm-up NaNs resolve to HOLD.
- Compression breakout defines squeeze as Bollinger upper/lower strictly inside
  Keltner upper/lower, requires at least six of the prior eight completed bars
  plus a squeezed previous bar, and uses a shifted Donchian upper level and
  relative volume.
- Pullback continuation uses previous RSI3 and previous close/EMA20, while
  structure slope and ADX use information available at the current bar.
- Mean reversion uses rolling Z-score `(close - SMA20) / sample_std20`, rolling
  VWAP `sum(typical_price * volume) / sum(volume)`, low ADX, tight EMA32/96,
  lower Bollinger breach, and RSI2. Explicit TRENDING/HIGH_VOLATILITY regimes
  block it.
- Relative strength uses 0.60 z(Return96/Vol96) plus 0.40
  z(Return16/Vol96), BTC EMA192 health, pair EMA96 eligibility, positive and
  above-median score, deterministic Score/Pair sorting, top two, and normalized
  inverse-volatility weights. `as_of` slices every pair before calculation;
  stale timestamps are excluded.
- Risk notional is `equity * risk_pct / stop_distance_fraction`, capped by
  maximum notional. Cooldown is inclusive at the configured bar count. Risk is
  multiplied by 0.5 from 6% drawdown and by 0.0 from 10%.

No shorts, leverage, future candles, threshold changes, or strategy enabling
were found. Inputs and repeated signal calls are deterministic. Professional
parameter files and definitions remain disabled.

## Proven issue and fix

The audit found that generic tuple/Series attachment inherited pandas names
such as `high`, `low`, and `close`, which could overwrite original OHLC columns
for Donchian, Keltner, and SMA outputs. Semantic registry output names now
prevent OHLCV mutation, and exhaustive tests assert exact preservation. The
existing ten strategies use legacy paths and remain exactly equivalent to the
pre-change HEAD outputs.

## Exit contract

Advanced exits are unsupported. Definitions explicitly identify either
`fixed_percent_full_position` or
`portfolio_overlay_not_single_pair_backtested`. Candidate result and trade
artifacts record the actual simulated mode. ATR trailing, time, indicator, and
partial exits remain metadata only.

## Performance

On cached 35,040-candle data, each corrected professional single-pair task took
about 0.09-0.11 seconds end-to-end. Twenty tasks (four strategies by five
pairs) completed in about 1.95 seconds, approximately 0.098 seconds/task,
preserving the Phase 20.10A target of roughly 0.58 seconds/task or better.
Indicator work accounted for about 1.24 seconds, signal work 0.16 seconds, and
backtesting 0.55 seconds in the representative run. Cross-sectional ranking
averaged 0.0052 seconds over 100 repeats; 100 template builds took 0.0215
seconds. Reusing the calculated Donchian output produced a 2.25x signal-only
micro-speedup with exact signals. A traced single-pair audit peak was 43.72 MiB;
combined multi-pair tracemalloc overhead was not used as a runtime claim.

No additional caching is justified. Registry resolution, JSON parsing, overlay
ranking, and allocation normalization are negligible. Persistent overlay
caching was rejected because input-version invalidation would add correctness
risk for no material benefit.

## Decision

The portfolio is safe to commit and safe to enable selectively for research.
It is not safe for paper trading or production approval without the progressive
research funnel. Phase 20.11 may begin after commit. Advanced exit support is a
separate future architecture phase, not a prerequisite for fixed-fallback
research as long as reports retain the simulated-exit disclosure.
