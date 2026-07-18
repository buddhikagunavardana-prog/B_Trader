from __future__ import annotations

import numpy as np
import pandas as pd

from src.trading_frameworks.models import FrameworkContext


def framework_frame(rows: int = 80, freq: str = "15min") -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq=freq, tz="UTC")
    base = np.linspace(100.0, 110.0, rows)
    frame = pd.DataFrame({
        "open": base - 0.2, "high": base + 0.7, "low": base - 0.7,
        "close": base, "volume": np.full(rows, 1500.0), "VOLUME_SMA": np.full(rows, 1000.0),
        "EMA": base - 1.0, "MACD": np.ones(rows), "MACD_SIGNAL": np.zeros(rows), "MACD_HISTOGRAM": np.ones(rows),
        "RSI": np.full(rows, 25.0), "STOCHASTIC_K": np.full(rows, 20.0), "FORCE_INDEX": np.ones(rows),
        "ATR": np.full(rows, 1.5), "ADX": np.full(rows, 22.0), "ZSCORE": np.full(rows, -2.0),
        "BOLLINGER_UPPER": base + 3.0, "BOLLINGER_MIDDLE": base + 1.0, "BOLLINGER_LOWER": base + 0.5,
        "DONCHIAN_UPPER": base + 1.0, "DONCHIAN_LOWER": base - 1.0,
        "DONCHIAN_EXIT_UPPER": base + 0.5, "DONCHIAN_EXIT_LOWER": base - 0.5,
        "ICHIMOKU_CONVERSION": base - 0.5, "ICHIMOKU_BASE": base - 1.0,
        "ICHIMOKU_SPAN_A": base - 2.0, "ICHIMOKU_SPAN_B": base - 3.0,
        "ICHIMOKU_LAGGING": base - 0.5,
    }, index=index)
    return frame


def context_for(name: str, rows: int = 80) -> FrameworkContext:
    if name == "triple_screen_trading":
        entry = framework_frame(rows, "5min")
        entry.loc[entry.index[-1], "close"] = entry.iloc[-2]["high"] + 1.0
        return FrameworkContext({
            "trend": framework_frame(max(2, rows // 12), "1h"),
            "setup": framework_frame(max(2, rows // 3), "15min"),
            "entry": entry,
        })
    frame = framework_frame(rows)
    if name in {"turtle_trading", "donchian_breakout"}:
        frame.loc[frame.index[-1], "close"] = frame.iloc[-2]["DONCHIAN_UPPER"] + 1.0
        frame.loc[frame.index[-1], "high"] = frame.iloc[-1]["close"] + 0.2
    return FrameworkContext({"execution": frame})
