# Trading Framework Library

Phase 24.3 registers exactly twenty stable reference frameworks. They are research-ready architectural baselines, not evidence of profitability. All signals use completed bars and precomputed indicator columns.

| Canonical name | Category | Roles and defaults | Required indicators |
|---|---|---|---|
| `triple_screen_trading` | Multi-timeframe | trend `1h`, setup `15m`, entry `5m` | EMA, MACD, RSI, Stochastic, Force Index, ATR |
| `turtle_trading` | Trend following | execution `1d` | Donchian Channel, ATR |
| `ichimoku_cloud_trading` | Trend following | execution `4h` | Ichimoku Cloud, ATR |
| `bollinger_mean_reversion` | Mean reversion | execution `15m` | Bollinger Bands, RSI, Z-Score, ADX, ATR |
| `donchian_breakout` | Breakout | execution `1h` | Donchian Channel, Volume SMA, ADX, ATR |

## Triple Screen Trading

Original concept: Alexander Elder's three-screen process combines a higher-timeframe trend, a counter-trend setup, and a lower-timeframe trigger. B Trader uses explicit `trend`, `setup`, and `entry` frames; it never builds those frames internally.

Defaults include 1h/15m/5m roles, RSI 40/60, Stochastic 30/70, 2 ATR stop, 2R target, and 1% risk hint. A long needs price above EMA with positive MACD histogram, an oversold setup with positive Force Index, and a completed close above the prior entry-bar high. Shorts mirror this. A trend reversal requests an exit. ADX and micro-Donchian are optional future extensions.

It fits trending pullback regimes and is incompatible with directionless ranges. It can miss entries when screens do not align and does not model discretionary Elder rules. Each role is sliced at the entry timestamp, so a future or unfinished higher-timeframe row is invisible. Research must validate timeframe ratios, markets, costs, and robustness.

## Turtle Trading

Original concept: the published Turtle approach combines channel breakouts, shorter opposite-channel exits, ATR/N risk, and controlled pyramiding. B Trader consumes externally prepared entry and exit Donchian columns and detects only completed-close breaks of the prior channel.

Defaults are 20-period entry, 55-period optional longer entry, 10-period exit, ATR/N 20, 2 ATR stop, 3R indicative target, 1% risk hint, and zero pyramiding units. It emits long/short entries and opposite-channel exits. Pyramiding is metadata only and remains disabled operationally.

It fits trends and volatility expansion, not quiet ranges. It does not implement the historical previous-breakout filter, portfolio unit limits, correlated-market controls, or actual pyramiding. Prior-row channels prevent the breakout candle from defining its own trigger. Transaction costs and gap execution require later research.

## Ichimoku Cloud Trading

Original concept: Ichimoku combines conversion/base relationships, Kumo location/state, and a lagging confirmation. B Trader supports continuation, Kumo breakout, and Tenkan/Kijun crossover modes with an optional causal lagging check.

Defaults are continuation mode, required lagging confirmation, standard confirmation strength, 2 ATR stop, 2.5R target, and 1% risk hint. Longs require price above the cloud and bullish conversion/base structure; shorts mirror it. Reversal structure can request an exit.

It fits trend and transition regimes, not choppy ranges. The indicator registry aligns displaced values to when they are available: the framework does not shift chart spans backward or expose future closes. This differs from conventional display plotting and must remain unchanged in research data. Signal variants still need market-specific validation.

## Bollinger Mean Reversion

Original concept: prices at statistical band extremes may revert toward a mean. B Trader requires outer-band location, RSI and Z-Score agreement, plus ADX below a range threshold. The middle band is the exit target.

Defaults are RSI 30/70, absolute Z-score 1.5, maximum ADX 25, 1.5 ATR stop, 1.5R target, 0.5% risk hint, and a 20-bar maximum-hold hint. It supports both directions and emits exits when an existing position reaches the middle band.

It fits ranges and low trend strength and is deliberately incompatible with strong trends and volatility breakouts. The holding-period value is not enforced in Phase 24.1. Band walking, gaps, and regime transitions can produce adverse signals; later research must include costs and tail risk.

## Donchian Breakout

Original concept: trade a break beyond a rolling price channel. This focused framework is separate from Turtle Trading: it uses a single breakout model with optional volume/ADX filters and does not carry Turtle System 1/System 2, previous-winner, unit, or portfolio rules.

Defaults are 20-period entry, 10-period exit, causal `close_break`, required volume confirmation, minimum ADX 20, 2 ATR stop, 2.5R target, and 1% risk hint. `high_low_break` and two-bar `confirmed_close` modes are available. Entries compare the trigger with the prior completed entry channel; exits use the prior completed exit channel.

It fits trends and volatility expansion, not quiet ranges. Volume comparability, false breaks, gaps, and slippage remain research risks. Current-bar Donchian values never serve as their own trigger.

## Research warning

No reference framework has been ranked, optimized, walk-forward tested, or shown profitable. Phase 24.1 decisions are deterministic architectural outputs. Phase 24.2 should add a research adapter and decision-series generation while preserving this release's no-network, no-order, no-look-ahead boundary.

## Phase 24.3 expansion

| Framework | Category | Dependencies | Completed-bar interpretation and principal defaults |
|---|---|---|---|
| `supertrend_trend_following` | Trend following | SuperTrend, EMA, ADX, ATR | Direction-confirmed SuperTrend state; 10/3, EMA 50, ADX 20, 2 ATR stop, 2.5R target. |
| `ema_ribbon_trend` | Trend following | EMA ribbon, ATR | Event when 8/13/21/34/55 ordering expands from a non-ordered state; compression prevents persistent entries. |
| `dual_moving_average_crossover` | Trend following | EMA or SMA, ATR | Event-only 20/50 cross; long and short; 2 ATR stop and 2R target. |
| `adx_trend_following` | Trend following | ADX, +DI, -DI, EMA, ATR | DI cross with ADX 25 and EMA confirmation; opposite DI event is the exit concept. |
| `parabolic_sar_trend` | Trend following | Parabolic SAR, EMA, ADX, ATR | Completed SAR direction flip with EMA confirmation; 0.02/0.2 SAR metadata. |
| `bollinger_squeeze_breakout` | Breakout | Bollinger Bands/Width, Keltner, ATR | Entry only on completed squeeze release beyond the prior band; distinct from persistent Keltner breaks. |
| `keltner_channel_breakout` | Breakout | Keltner, EMA, ATR | Completed close crosses a prior channel boundary; center-line return is the exit concept. |
| `atr_volatility_breakout` | Breakout | ATR, EMA | Close exceeds prior close ± 1.5 prior ATR; stop 2 ATR, target 2R. |
| `opening_range_breakout` | Breakout | OHLC, ATR | Generic UTC session, six completed opening bars, fixed range, close confirmation; no exchange calendar. |
| `rsi_pullback_trend` | Momentum | RSI, EMA, ADX, ATR | Recovery event after 40/60 pullback setup through 45/55 trigger; never enters on the initial extreme. |
| `macd_momentum` | Momentum | MACD, EMA, ADX, ATR | Event-only MACD/signal cross with histogram and EMA confirmation. |
| `vwap_mean_reversion` | Mean reversion | VWAP, VWAP Deviation, RSI, ATR | Cumulative canonical VWAP by default—no assumed session reset; deviation 1.5 and RSI 30/70. |
| `zscore_mean_reversion` | Mean reversion | Z-Score, EMA, ATR | Recovery from ±2 extremes toward 0.25; 20-bar maximum-hold hint. |
| `inside_bar_breakout` | Price action | OHLC, ATR | Mother-bar level is fixed only after the inside bar closes; confirmed-close default, three-bar expiry hint. |
| `support_resistance_bounce` | Price action | Support/Resistance, swings, RSI, ATR | Uses externally prepared, previously confirmed levels; ATR zone tolerance avoids future swing leakage. |

All expansion entries are stateless event models. Crosses, flips, releases, recoveries, and mother-bar breaks are emitted on transition rather than on every candle in a persistent state. Stops and targets are advisory; position-aware exit enforcement remains downstream. Turtle retains its System 1/System 2 and N-risk interpretation, while generic Donchian is a filtered single-channel breakout. Bollinger Squeeze requires containment then release; Keltner Breakout is simply a prior-boundary cross. Opening Range sessions are configurable data conventions, not exchange calendars. Support/resistance inputs must already be causally confirmed.

Phase 24.4 retains stateless framework implementations while the research adapter tracks advisory position, setup, and session lifecycles. Opening Range uses stable session IDs; Inside Bar, RSI Pullback, Support/Resistance, and Bollinger Squeeze use consumable setup identities so repeated signals can be suppressed without hidden framework state.
