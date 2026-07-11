import json
import os
from pathlib import Path

import pandas as pd

from src.data.data_cache_engine import get_cached_klines
from src.indicators.market_strength.adx import calculate_adx
from src.indicators.trend.ema import calculate_ema
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.bollinger import calculate_bollinger
from src.indicators.volume.volume import calculate_volume_sma


CONFIG_PATH = Path("src/config/market_regime.json")
REPORT_PATH = "reports/market_regime_report.csv"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
TIMEFRAME = "15m"
LOOKBACK = "1 year ago UTC"

REGIME_STRATEGY_FAMILIES = {
    "TRENDING": ["EMA", "SuperTrend", "Trend Following"],
    "SIDEWAYS": ["Bollinger", "RSI Mean Reversion"],
    "HIGH_VOLATILITY": ["ATR Breakout", "Donchian Breakout"],
    "LOW_VOLATILITY": ["Squeeze", "Low Volatility"],
}


def load_market_regime_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _latest_clean_row(df: pd.DataFrame):
    clean_df = df.dropna().copy()

    if clean_df.empty:
        raise ValueError("Not enough data to detect market regime")

    return clean_df.iloc[-1]


def _score_regimes(row, config: dict) -> dict:
    adx_value = row["ADX14"]
    atr_pct = row["ATR_PCT"]
    bollinger_width = row["BB_WIDTH_PCT"]
    ema_distance = row["EMA_DISTANCE_PCT"]
    volume_ratio = row["VOLUME_RATIO"]

    scores = {
        "TRENDING": 0,
        "SIDEWAYS": 0,
        "HIGH_VOLATILITY": 0,
        "LOW_VOLATILITY": 0,
    }
    reasons = {regime: [] for regime in scores}

    if adx_value >= config["adx"]["trending_min"]:
        scores["TRENDING"] += 2
        reasons["TRENDING"].append(f"ADX strong at {adx_value:.2f}")

    if ema_distance >= config["ema_distance"]["trending_min_pct"]:
        scores["TRENDING"] += 2
        reasons["TRENDING"].append(
            f"EMA50/EMA200 distance {ema_distance:.2f}%"
        )

    if adx_value <= config["adx"]["sideways_max"]:
        scores["SIDEWAYS"] += 2
        reasons["SIDEWAYS"].append(f"ADX weak at {adx_value:.2f}")

    if ema_distance <= config["ema_distance"]["sideways_max_pct"]:
        scores["SIDEWAYS"] += 1
        reasons["SIDEWAYS"].append(
            f"EMA50/EMA200 distance tight at {ema_distance:.2f}%"
        )

    if bollinger_width <= config["bollinger_width"]["sideways_max_pct"]:
        scores["SIDEWAYS"] += 1
        reasons["SIDEWAYS"].append(
            f"Bollinger width contained at {bollinger_width:.2f}%"
        )

    if atr_pct >= config["atr"]["high_volatility_pct"]:
        scores["HIGH_VOLATILITY"] += 2
        reasons["HIGH_VOLATILITY"].append(f"ATR high at {atr_pct:.2f}%")

    if bollinger_width >= config["bollinger_width"]["high_volatility_pct"]:
        scores["HIGH_VOLATILITY"] += 2
        reasons["HIGH_VOLATILITY"].append(
            f"Bollinger width wide at {bollinger_width:.2f}%"
        )

    if volume_ratio >= config["volume_ratio"]["high_volatility_min"]:
        scores["HIGH_VOLATILITY"] += 1
        reasons["HIGH_VOLATILITY"].append(
            f"Volume ratio elevated at {volume_ratio:.2f}"
        )

    if atr_pct <= config["atr"]["low_volatility_pct"]:
        scores["LOW_VOLATILITY"] += 2
        reasons["LOW_VOLATILITY"].append(f"ATR low at {atr_pct:.2f}%")

    if bollinger_width <= config["bollinger_width"]["low_volatility_pct"]:
        scores["LOW_VOLATILITY"] += 2
        reasons["LOW_VOLATILITY"].append(
            f"Bollinger width narrow at {bollinger_width:.2f}%"
        )

    if volume_ratio <= config["volume_ratio"]["low_volatility_max"]:
        scores["LOW_VOLATILITY"] += 1
        reasons["LOW_VOLATILITY"].append(
            f"Volume ratio quiet at {volume_ratio:.2f}"
        )

    return scores, reasons


def detect_market_regime(df: pd.DataFrame, config: dict | None = None) -> dict:
    config = config or load_market_regime_config()
    lookback_candles = config.get("lookback_candles", 200)
    regime_df = df.tail(lookback_candles).copy()

    regime_df["EMA50"] = calculate_ema(regime_df, 50)
    regime_df["EMA200"] = calculate_ema(regime_df, 200)
    regime_df["ADX14"] = calculate_adx(regime_df)
    regime_df["ATR14"] = calculate_atr(regime_df)
    (
        regime_df["BB_UPPER"],
        regime_df["BB_MIDDLE"],
        regime_df["BB_LOWER"],
    ) = calculate_bollinger(regime_df)
    regime_df["VOLUME_SMA20"] = calculate_volume_sma(regime_df)

    regime_df["ATR_PCT"] = regime_df["ATR14"] / regime_df["close"] * 100
    regime_df["BB_WIDTH_PCT"] = (
        (regime_df["BB_UPPER"] - regime_df["BB_LOWER"])
        / regime_df["BB_MIDDLE"]
        * 100
    )
    regime_df["EMA_DISTANCE_PCT"] = (
        (regime_df["EMA50"] - regime_df["EMA200"]).abs()
        / regime_df["close"]
        * 100
    )
    regime_df["VOLUME_RATIO"] = (
        regime_df["volume"] / regime_df["VOLUME_SMA20"]
    )

    latest = _latest_clean_row(regime_df)
    scores, reasons = _score_regimes(latest, config)
    regime = max(scores, key=scores.get)
    max_possible_score = 5
    confidence = round(min(scores[regime] / max_possible_score, 1.0), 2)

    if not reasons[regime]:
        reasons[regime].append("No strong signal; using highest relative score")

    return {
        "regime": regime,
        "confidence": confidence,
        "reasons": reasons[regime],
    }


def get_recommended_strategy_family(regime: str) -> str:
    return ", ".join(REGIME_STRATEGY_FAMILIES.get(regime, []))


def run_market_regime_engine():
    config = load_market_regime_config()
    rows = []

    print("\n===== B TRADER MARKET REGIME ENGINE =====")

    for symbol in SYMBOLS:
        print(f"Detecting regime: {symbol} | Timeframe: {TIMEFRAME}")
        df = get_cached_klines(
            symbol=symbol,
            timeframe=TIMEFRAME,
            lookback=LOOKBACK,
        )
        result = detect_market_regime(df, config)

        latest_date = pd.to_datetime(df["open_time"]).max().date().isoformat()
        rows.append({
            "Pair": symbol,
            "Date": latest_date,
            "Regime": result["regime"],
            "Confidence": result["confidence"],
            "Reasons": " | ".join(result["reasons"]),
            "Recommended Strategy Family": get_recommended_strategy_family(
                result["regime"]
            ),
        })

    report = pd.DataFrame(rows)
    os.makedirs("reports", exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)

    print(f"\nReport saved -> {REPORT_PATH}")
    print(report.to_string(index=False))

    return report


if __name__ == "__main__":
    run_market_regime_engine()
