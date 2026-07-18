# B Trader Professional Indicator Library

B Trader exposes 122 registered indicators through
`src.indicators.registry.indicator_registry`. The registry validates JSON
parameters and required columns, supplies documented defaults and output
metadata, resolves backward-compatible names, validates dependencies, and
attaches newly enabled indicators to the research DataFrame without manual
engine imports. The detailed framework and gap inventory is maintained in
`reports/indicator_framework_inventory.csv`.

## Inventory

### Trend (22)

EMA, SMA, WMA, VWMA, HMA, DEMA, TEMA, KAMA, SuperTrend, and Ichimoku Cloud.
Parabolic SAR provides both its trailing level and direction. Phase 23.2 adds
Linear Regression Trend, TRIMA, ALMA, ZLEMA, McGinley Dynamic, FRAMA, VIDYA,
Moving Average Envelope, Linear Regression Slope, Time Series Forecast, and a
causally aligned DPO.

### Momentum (34)

RSI, MACD, Stochastic, Stochastic RSI, CCI, Williams %R, ROC, Momentum, TSI,
Ultimate Oscillator, and rolling Z-score.
TRIX, PPO, APO, CMO, Connors RSI, RMI, Fisher Transform, Awesome Oscillator,
Balance of Power, and Coppock Curve complete the Phase 23.2 expansion. Ultimate
Oscillator was already canonical and was not duplicated.
Phase 23.3 adds Accelerator Oscillator, Schaff Trend Cycle, KST, SMI Ergodic,
DeMarker, Qstick, Relative Vigor Index, Center of Gravity, Chande Forecast
Oscillator, Pretty Good Oscillator, Stochastic Momentum Index, Psychological
Line, and Rainbow Oscillator.

### Volatility (22)

ATR, Bollinger Bands, Keltner Channel, Donchian Channel, Historical
Volatility, Standard Deviation, and Chaikin Volatility.
Bollinger Band Width, Bollinger Percent B, Chandelier Exit, Normalized ATR,
Ulcer Index, and Mass Index reuse existing components where applicable.
Chaikin Volatility was already canonical and was not duplicated.
True Range, Volatility Stop, ATR Bands, causally confirmed Fractal Chaos Bands,
Moving Standard Deviation Channel, Donchian Width, Keltner Width, Parkinson
Volatility, and Garman-Klass Volatility were added in Phase 23.3.

### Volume (25)

OBV, VWAP, CMF, MFI, Accumulation/Distribution, Volume ROC, Ease of Movement,
rolling VWAP, and the backward-compatible Volume SMA used by existing
strategies. The first seven constituted the Phase 20.10B library target set;
rolling VWAP and Z-score support the professional strategy portfolio.
Force Index, Volume EMA, Chaikin Oscillator, Negative Volume Index, and Positive
Volume Index are registered with deterministic warm-up and output conventions.
Phase 23.3 adds Klinger Oscillator, Price Volume Trend, Volume Oscillator,
Twiggs Money Flow, Volume Weighted MACD, Intraday Intensity Index, Money Flow
Volume, Volume Zone Oscillator, Net Volume, VWAP Deviation, and Money Flow
Oscillator.

### Market strength (8)

ADX, Aroon, Vortex, Choppiness Index, DMI, and Elder Ray Index.
Standalone Plus DI and Minus DI views reuse the shared DMI calculation.

### Structure (10)

Pivot Points, Support/Resistance, Swing High/Low, Price Channels, Fibonacci
Retracement, and Linear Regression Channel.
Breakout Detection uses only prior rolling extrema. Fair Value Gap, Order Block,
and BOS/CHoCH are deterministic rule-based approximations and are marked
experimental rather than representations of institutional order flow.

## Experimental structure rules

Fair Value Gap is confirmed on the third candle of a three-candle gap and emits
bounds only at confirmation time. Order Block uses the previous opposite candle
as a candidate and emits it only after a close breaks the prior rolling range.
BOS/CHoCH compares the current close with prior rolling extremes and maintains a
causal direction state. These outputs are event based; downstream strategies
must manage persistence and invalidation after a close crosses the reported
bounds. Future candles and centered windows are not used.

### Candlestick (1 engine)

The existing vectorized candlestick-pattern engine is registered once and is
not duplicated. It currently detects 26 named patterns.

## JSON usage

Indicators are configured under the existing strategy `indicators` mapping:

```json
{
  "indicators": {
    "kama": {"enabled": true, "period": 10},
    "vortex": {"enabled": true, "period": 14},
    "linear_regression_channel": {
      "enabled": true,
      "period": 20,
      "deviations": 2.0,
      "source": "close"
    }
  }
}
```

Unknown names, unknown parameters, non-dictionary settings, non-positive
periods, and invalid multipliers are rejected while loading JSON. The
`enabled` key controls pipeline execution and is not passed into indicator
functions.

Backward-compatible aliases include `bollinger`, `keltner`, `donchian`,
`volume`, `adl`, `swing`, and `fibonacci`.

## Python usage

```python
from src.indicators.registry import indicator_registry

kama = indicator_registry.calculate("kama", market_df, {"period": 10})
definition = indicator_registry.get("kama")
trend_names = indicator_registry.list_by_category("trend")
```

Single-output indicators return an index-aligned `pandas.Series`.
Multi-output indicators return Series tuples (semantic names where available,
otherwise deterministic registry names), and structured level sets
return dictionaries of index-aligned Series. Candlestick patterns return a
DataFrame. Empty inputs with the required OHLCV columns retain the empty index;
warm-up windows and unavailable calculations use pandas/NumPy `NaN` semantics.

## Compatibility and performance

Existing indicator formulas and existing strategy execution paths remain
unchanged. New indicators use vectorized pandas/NumPy calculations except for
recursive definitions such as KAMA and SuperTrend, where a deterministic
single pass is mathematically required. Registry calculations do not copy the
input DataFrame. The existing candlestick implementation is reused.

## Phase 23.3 canonical mappings

Elder Ray Index, Standard Deviation, Price Channels, and Force Index already
cover the requested Elder Ray, Standard Deviation, Price Channel, and Elder
Force Index tools. PPO already exposes `PPO_HISTOGRAM`. Price Volume Trend and
Volume Price Trend are the same canonical PVT calculation. Klinger Oscillator
and Klinger Volume Oscillator use the single `klinger_oscillator` registration.
Same-category replacements were added so canonical mapping did not reduce the
phase target count; the exact mappings and replacements are recorded in the
inventory.

## Indicator-engine attachment debt

Registry calculations are validated independently, but the legacy indicator
engine still attaches enabled outputs one column at a time. Batching was
deferred because the current public behavior mutates the supplied DataFrame and
allows a later configured indicator to use a column attached earlier in the
same call. A safe future change needs to preserve both behaviors and duplicate
column handling before replacing attachment with `pandas.concat`.
