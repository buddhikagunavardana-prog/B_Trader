# B Trader Professional Indicator Library

B Trader exposes 51 registered indicators through
`src.indicators.registry.indicator_registry`. The registry validates JSON
parameters and required columns, supplies documented defaults and output
metadata, resolves backward-compatible names, validates dependencies, and
attaches newly enabled indicators to the research DataFrame without manual
engine imports. The detailed framework and gap inventory is maintained in
`reports/indicator_framework_inventory.csv`.

## Inventory

### Trend (11)

EMA, SMA, WMA, VWMA, HMA, DEMA, TEMA, KAMA, SuperTrend, and Ichimoku Cloud.
Parabolic SAR provides both its trailing level and direction.

### Momentum (11)

RSI, MACD, Stochastic, Stochastic RSI, CCI, Williams %R, ROC, Momentum, TSI,
Ultimate Oscillator, and rolling Z-score.

### Volatility (7)

ATR, Bollinger Bands, Keltner Channel, Donchian Channel, Historical
Volatility, Standard Deviation, and Chaikin Volatility.

### Volume (9)

OBV, VWAP, CMF, MFI, Accumulation/Distribution, Volume ROC, Ease of Movement,
rolling VWAP, and the backward-compatible Volume SMA used by existing
strategies. The first seven constituted the Phase 20.10B library target set;
rolling VWAP and Z-score support the professional strategy portfolio.

### Market strength (6)

ADX, Aroon, Vortex, Choppiness Index, DMI, and Elder Ray Index.

### Structure (6)

Pivot Points, Support/Resistance, Swing High/Low, Price Channels, Fibonacci
Retracement, and Linear Regression Channel.

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
