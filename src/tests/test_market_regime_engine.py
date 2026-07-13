import pandas as pd

from src.research.market_regime_engine import (
    detect_historical_market_regimes,
    detect_market_regime,
)


def _market_data(rows: int = 240) -> pd.DataFrame:
    closes = [100.0 + index * 0.02 for index in range(rows)]
    return pd.DataFrame({
        "open_time": pd.date_range(
            "2025-01-01T00:00:00Z",
            periods=rows,
            freq="15min",
        ),
        "open": closes,
        "high": [value + 0.5 for value in closes],
        "low": [value - 0.5 for value in closes],
        "close": closes,
        "volume": [100.0 + index % 7 for index in range(rows)],
    })


def test_latest_regime_contract_remains_available():
    result = detect_market_regime(_market_data())

    assert result["regime"] in {
        "TRENDING",
        "SIDEWAYS",
        "HIGH_VOLATILITY",
        "LOW_VOLATILITY",
    }
    assert 0 <= result["confidence"] <= 1
    assert result["reasons"]


def test_historical_regime_uses_only_prior_completed_candle():
    baseline = _market_data()
    changed = baseline.copy()
    changed.loc[changed.index[-1], ["high", "close", "volume"]] = [
        1000.0,
        900.0,
        100000.0,
    ]

    baseline_history = detect_historical_market_regimes(baseline)
    changed_history = detect_historical_market_regimes(changed)

    assert baseline_history.iloc[-1]["Regime"] == changed_history.iloc[-1]["Regime"]
    assert (
        baseline_history.iloc[-1]["Confidence"]
        == changed_history.iloc[-1]["Confidence"]
    )
    assert pd.isna(baseline_history.iloc[0]["Regime"])


if __name__ == "__main__":
    test_latest_regime_contract_remains_available()
    test_historical_regime_uses_only_prior_completed_candle()
    print("test_market_regime_engine passed")
