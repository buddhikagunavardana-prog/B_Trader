# Professional Quantitative Strategy Portfolio

This portfolio adds five deterministic Binance Spot, long-only research
families for the five-pair 15-minute universe. Every definition starts disabled
with status `RESEARCH_CANDIDATE`; none is production-approved or claimed to be
profitable.

## Roles

- Core: Volatility-Scaled Time-Series Momentum, Compression-to-Expansion
  Donchian Breakout, and Trend Pullback Continuation.
- Overlay: Cross-Sectional Relative Strength Rotation.
- Satellite: Regime-Gated Intraday Mean Reversion.

The cross-sectional model is a portfolio selector rather than a forced
single-pair signal strategy. It ranks eligible pairs using 16/96-bar
volatility-adjusted momentum, applies the BTC health filter, selects at most two
pairs, and assigns inverse-volatility weights capped at total spot notional of
1.0 by configuration.

## Default behavior and regimes

Time-series momentum uses EMA 32/96, ADX 14, a previous-20-bar breakout, and
ATR risk metadata. Compression breakout requires six of the prior eight squeeze
bars, a previous-bar squeeze, a previous-20-bar breakout, upper Bollinger break,
and relative volume. Pullback continuation uses EMA 20/48/192 with previous-bar
RSI 3 and previous-close pullback confirmation. Mean reversion requires low ADX,
tight EMA 32/96 distance, negative Z-score, lower Bollinger breach, RSI 2, and
rolling VWAP, and is blocked in trend/breakout/shock regimes.

Routing lives in `src/config/professional_strategy_portfolio.json`. Strong
trends route to trend strategies, high volatility routes to breakout/trend,
sideways/low-volatility routes only to mean reversion, and volatility shock
blocks new entries. Unknown regimes use reduced-risk momentum defaults.

## Risk and exit limitations

Shared helpers provide risk-per-trade notional sizing, same-pair cooldowns, and
the 6%/10% drawdown throttle. No leverage, shorts, margin, or futures logic is
introduced.

The current backtest engine supports full-position fixed percentage SL/TP only.
It does not support partial exits, ATR trailing stops, indicator exits, or time
exits. Strategy JSON records the preferred professional exits but uses explicit
fixed full-exit fallbacks for compatibility. This limitation must be addressed
through a separately reviewed generic backtest enhancement before those exit
rules can be evaluated faithfully.

Every definition declares `simulated_exit_mode`. Single-pair research artifacts
record `fixed_percent_full_position`; the cross-sectional definition records
`portfolio_overlay_not_single_pair_backtested`. Preferred ATR, trailing,
indicator, time, and partial exits are metadata only and must never be reported
as simulated by the current engine.

## Research workflow

To research a single-pair family, enable its JSON definition under
`src/strategies/definitions` and run the existing fixed/generated research,
walk-forward, regime, robustness, Monte Carlo, and portfolio pipeline. Do not
enable the cross-sectional overlay as an ordinary single-pair candidate; call
`rank_relative_strength` from the portfolio research layer with synchronized
pair DataFrames.

The empty professional research report schema includes performance,
walk-forward, robustness, Monte Carlo, consistency, stability, portfolio, and
holding-period fields. Values remain unavailable until genuine research is run.
Generated reports are not committed by this integration phase.

## Weaknesses

Trend systems can whipsaw, compression breakouts can fail after false
expansion, pullbacks can become reversals, mean reversion is vulnerable to
regime misclassification, and relative-strength rotation can incur turnover and
concentrated correlated exposure. Default parameters are research baselines,
not optimized recommendations.
