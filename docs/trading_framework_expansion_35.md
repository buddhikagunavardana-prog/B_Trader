# Professional Trading Framework Expansion to 35

Phase 24.6 adds fifteen completed-bar research frameworks. Every entry is deterministic, long/short capable, state-policy compatible, and limited to advisory stops, targets, trailing levels, and holding hints. None sizes orders, models fills, reads balances, connects to a venue, or calculates profitability.

## Momentum and mean reversion

### Elder Impulse System

`elder_impulse_system` is a momentum framework attributed to Alexander Elder's impulse concept. EMA 13 slope and MACD 12/26/9 histogram change define bullish, bearish, or neutral state; ADX 20 can qualify strength. A transition into aligned positive components proposes long, aligned negative proposes short, and neutral/opposite state proposes exit. ATR 14 supplies a 2 ATR stop and 2R target/trailing hint. Entry transitions are consumed by policy. It fits directional momentum, differs from `macd_momentum` by requiring simultaneous EMA slope and histogram change, and remains vulnerable to choppy color changes. Only current and prior completed values are read.

### Connors RSI Mean Reversion

`connors_rsi_mean_reversion` combines 3-period price RSI, 2-period streak RSI, and a causal 100-row percent rank, with EMA 200 trend filtering. Recovery above 10 while above trend proposes long; recovery below 90 while below trend proposes short; 50 or a 10-bar advisory hold ends the proposal. Setups expire and consume through policy. ATR supplies advisory risk. Unlike normal RSI Pullback, this is a three-component extreme/percent-rank model rather than a single RSI trend recovery. Percent rank uses historical windows only.

### Stochastic Pullback Trend

`stochastic_pullback_trend` is momentum: Stochastic 14/3 enters a 25/75 pullback zone inside an EMA 50, ADX 20 trend, then a completed K/D recovery cross triggers once. Opposite K/D state proposes exit. The setup has a five-bar lifetime, trend invalidation, and event consumption. ATR 14 supplies advisory risk. It fits established trends and can whipsaw in ranges; no unfinished cross is visible.

### Williams Percent R Reversal

`williams_r_reversal` is mean reversion: Williams %R 14 must first reach -80/-20, then cross the configured -70/-30 recovery level with EMA 100 context. The -50 mean is the exit. Five-bar setup expiry and one-shot consumption apply. ATR provides risk proposals. The extreme must exist in prior completed history; persistent threshold state is not an event.

### CCI Trend Pullback

`cci_trend_pullback` is momentum: EMA 50 and ADX 20 qualify trend, CCI 20 arms below -100 or above +100, and recovery through -50/+50 triggers long/short. Opposite recovery proposes exit. The setup expires after five bars and is consumed once. ATR 14 provides advisory stop/target. It fits trend pullbacks, not directionless CCI oscillation, and uses causal crossings.

## Trend following

### Chandelier Exit Trend

`chandelier_exit_trend` uses Chandelier 22/22/3 and EMA 50. Price transition beyond the prior completed long/short Chandelier reference proposes entry; breach of the prior trailing level proposes exit. The level is exposed as trailing metadata, with ATR risk controls. Unlike SuperTrend, Chandelier is a rolling-extreme exit reference rather than a continuously switching directional band. Current highs/lows never define their own trigger.

### Price Channel Trend

`price_channel_trend` breaks a prior 20-row price channel with EMA 50 confirmation and exits at the center line. ATR 14 provides risk proposals and entries are event-consumed. It is a single price-channel trend model: Donchian Breakout adds its own filters, Turtle uses separate entry/exit systems and portfolio heritage, and Keltner uses EMA plus ATR envelopes. Prior channel rows prevent self-trigger leakage.

### Heikin Ashi Trend

`heikin_ashi_trend` recursively derives HA close and HA open; the first HA open is the raw open/close midpoint and later opens use prior HA open/close. A clean bullish/bearish transition, limited counter-trend wick, EMA 50, and ADX 20 propose entry; neutral/opposite HA state proposes exit. ATR 14 supplies advisory risk. Persistent color is state, not a repeated event. Recursive values use no future candle.

### Aroon Trend

`aroon_trend` uses Aroon 25, strong/weak thresholds 70/30, EMA 50, and ATR 14. A new Up-dominant state proposes long, Down-dominant proposes short, and dominance reversal/neutral oscillator proposes exit. State transitions are consumed. It fits directional recency trends and is vulnerable to rapid range-bound dominance switches. Rolling extrema are completed-bar causal.

## Breakout

### Momentum Acceleration Breakout

`momentum_acceleration_breakout` requires a close beyond the prior 20-row price channel, ROC 10 beyond ±1 and accelerating, Momentum 10 accelerating, plus EMA 50 direction. Center-line failure proposes exit and policy tracks false-break invalidation/expiry. ATR 14 provides risk proposals. Channel and acceleration use only past/current completed rows.

### Volume Expansion Breakout

`volume_expansion_breakout` requires a prior 20-row channel break and volume at least 1.5 times the prior 20-row volume SMA, with EMA 50 context. Zero/missing average volume cannot confirm; low-volume breaks receive false-break diagnostics. Center line proposes exit; setup expiry and event consumption apply. ATR 14 supplies risk. No volume normalization is inferred across venues.

### Pivot Range Breakout

`pivot_range_breakout` uses only the previous completed session's high, low, and close to derive pivot, R1, and S1. A completed cross of R1/S1 with EMA 50 direction proposes entry; pivot return proposes exit. Levels carry a deterministic prior-session ID, expire on configured rollover, and support daily or boundary-shifted sessions without network calendars. ATR supplies risk. Unlike Opening Range Breakout, no active-session future high/low contributes to the level.

## Price action

### NR4/NR7 Volatility Breakout

`nr4_nr7_volatility_breakout` identifies a completed candle whose high-low range is the narrowest of four or seven rows. The next confirmed close beyond its high/low proposes long/short; the midpoint is the exit reference. Timestamp-derived setup IDs, three-bar expiry, nested setup handling, and one-shot consumption apply. ATR 14 supplies risk. Unlike Inside Bar, NR does not require containment inside a mother candle.

### Pin Bar Rejection

`pin_bar_rejection` requires a wick at least twice the body, body no more than 30% of range, and rejection within 0.5 ATR of externally confirmed support/resistance. Bullish/bearish rejection proposes entry; structural level failure proposes exit. Level IDs/retest policy, two-bar setup expiry, and event consumption apply. ATR provides risk. Unlike generic Support/Resistance Bounce, the bounded candle geometry is mandatory. Level inputs must already be causally confirmed.

### Engulfing Confirmation Trend

`engulfing_confirmation_trend` uses completed bullish/bearish engulfing flags, EMA 50, ADX 20, and ATR 14. Pattern plus matching trend proposes entry; opposite pattern proposes exit. Strict/relaxed mode is explicit metadata, pattern IDs use completed timestamps, and each pattern is consumed once. Unlike a generic candlestick catalog, the pattern cannot act without trend context. Optional volume confirmation remains metadata-only unless prepared.

## Shared implementation and limitations

All parameter definitions have types, bounded defaults, descriptions, unknown-field rejection, and cross-field checks. `COMPUTE_MISSING` uses canonical indicators with parameter fingerprints, component aliases, request deduplication, collision rejection, and source-copy preservation. Heikin Ashi, NR4/NR7, and prior-session pivots are causal derived requests with the same provenance contract. `PRECOMPUTED_ONLY` remains the default.

The normalized adapter schema is unchanged and state fields remain optional extensions. Setup/event frameworks reset per run, suppress repeated entries, and use Phase 24.5 cooldown, opposite-signal, maximum-hold, rollover, and level policies. These are structural research implementations; holiday calendars, market-specific session conventions, costs, fills, execution latency, and historical efficacy require later phases.

## Performance validation

The release benchmark covers all 35 canonical frameworks at 1,000 and 10,000 rows in stateless, stateful-policy, and stateful-policy-with-instrumentation modes. Each of the 210 cases has one warm-up and three measured runs. At 10,000 rows, mean total time per framework is 3,514.410 ms stateless, 5,048.367 ms stateful-policy, and 5,112.533 ms with instrumentation. The exact Phase 24.5 10,000-row baseline read from `framework_state_performance.csv` is 2,916.610 ms, so the expanded stateful-policy mix is 73.1% higher; instrumentation adds 1.27% over the non-instrumented stateful-policy mode.

Scaling from 1,000 to 10,000 rows is 10.33x stateless, 10.30x stateful-policy, and 10.26x instrumented. Every case reports zero repeated indicator calculations, so the matrix shows no nonlinear scaling or dependency-recalculation defect. The five slowest frameworks by mean across the three 10,000-row modes are Opening Range Breakout (6,853.107 ms), Stochastic Pullback Trend (6,042.798 ms), CCI Trend Pullback (5,972.203 ms), Williams Percent R Reversal (5,914.499 ms), and Triple Screen Trading (5,659.982 ms). Among the new frameworks, Pin Bar Rejection (5,312.661 ms) and Volume Expansion Breakout (4,802.102 ms) follow the three new oscillator frameworks in that list.

The higher aggregate is retained as medium performance follow-up rather than treated as a release blocker: causality, deterministic output, source preservation, state-policy correctness, and linear scaling all pass. A later performance-only phase may profile repeated rolling scans in the slowest frameworks, but must not weaken completed-bar or policy guarantees.

Phase 24.7 completed that follow-up. Its five-run 10,000-row stateful-policy median average is 3,390.445 ms/framework, 32.84% below the Phase 24.6 reference. Aggregate instrumentation overhead is 0.714%, scaling is 9.581x, and repeated calculations remain zero. The prior Opening Range hotspot was replaced with a causal one-pass run-owned range context; remaining oscillator and multi-timeframe costs are documented in `framework_performance_architecture.md`.
