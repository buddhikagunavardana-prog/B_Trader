from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.engines.indicator_engine import calculate_indicators


def _market_data(rows: int = 160) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="15min")
    base = np.linspace(100.0, 140.0, rows)
    return pd.DataFrame(
        {
            "open": base - 0.2,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + np.sin(np.arange(rows) / 5.0),
            "volume": np.linspace(1_000.0, 3_000.0, rows),
        },
        index=index,
    )


def test_registered_indicators_attach_to_engine_dataframe() -> None:
    market = _market_data()
    original = market.copy(deep=True)
    strategy = SimpleNamespace(
        indicators={
            "parabolic_sar": {"enabled": True},
            "ichimoku_cloud": {"enabled": True},
            "stochastic_rsi": {"enabled": True},
            "obv": {"enabled": True},
        },
    )
    result = calculate_indicators(market.copy(), strategy)
    expected = {
        "PARABOLIC_SAR",
        "PARABOLIC_SAR_DIRECTION",
        "ICHIMOKU_CONVERSION",
        "ICHIMOKU_LAGGING",
        "STOCHASTIC_RSI_K",
        "STOCHASTIC_RSI_D",
        "OBV",
    }
    assert expected.issubset(result.columns)
    assert result.index.equals(original.index)
    pd.testing.assert_frame_equal(result[original.columns], original)


if __name__ == "__main__":
    test_registered_indicators_attach_to_engine_dataframe()
    print("test_indicator_engine passed")
