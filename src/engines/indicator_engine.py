from src.indicators.trend.ema import calculate_ema
from src.indicators.momentum.rsi import calculate_rsi
from src.indicators.momentum.macd import calculate_macd
from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.bollinger import calculate_bollinger
from src.indicators.market_strength.adx import calculate_adx
from src.indicators.volume.volume import calculate_volume_sma
from src.indicators.structure.support_resistance import calculate_support_resistance
from src.indicators.candlestick.candlestick import detect_candle_pattern
from src.indicators.registry import indicator_registry


LEGACY_ENGINE_INDICATORS = {
    "ema", "rsi", "macd", "atr", "bollinger", "bollinger_bands",
    "volume", "volume_sma", "support_resistance", "candlestick",
    # SuperTrend was historically configured but not attached by this engine.
    # Keep that behavior until strategy logic is intentionally revised.
    "supertrend",
}


def _attach_registry_output(df, name, output):
    if isinstance(output, tuple):
        for index, item in enumerate(output, start=1):
            column = item.name or f"{name.upper()}_{index}"
            df[column] = item
    elif isinstance(output, dict):
        prefix = name.upper()
        for key, item in output.items():
            df[f"{prefix}_{key}"] = item
    elif hasattr(output, "columns"):
        for column in output.columns:
            df[column] = output[column]
    else:
        column = output.name or name.upper()
        df[column] = output

def calculate_indicators(df, strategy):

    indicators = strategy.indicators

    # =====================
    # EMA
    # =====================

    ema = indicators.get("ema", {})

    if ema.get("enabled", False):

        fast = ema.get("fast", 20)
        slow = ema.get("slow", 50)
        trend = ema.get("trend", 200)

        df[f"EMA{fast}"] = calculate_ema(df, fast)
        df[f"EMA{slow}"] = calculate_ema(df, slow)
        df[f"EMA{trend}"] = calculate_ema(df, trend)

    # =====================
    # RSI
    # =====================

    rsi = indicators.get("rsi", {})

    if rsi.get("enabled", False):

        period = rsi.get("period", 14)

        df[f"RSI{period}"] = calculate_rsi(df, period)

    # =====================
    # MACD
    # =====================

    macd = indicators.get("macd", {})

    if macd.get("enabled", False):

        df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(
            df,
            macd.get("fast", 12),
            macd.get("slow", 26),
            macd.get("signal", 9),
        )

    # =====================
    # ATR
    # =====================

    atr = indicators.get("atr", {})

    if atr.get("enabled", False):

        period = atr.get("period", 14)

        df[f"ATR{period}"] = calculate_atr(df, period)

    # =====================
    # Other Indicators
    # =====================

    df["BB_UPPER"], df["BB_MIDDLE"], df["BB_LOWER"] = calculate_bollinger(df)

    df["ADX14"] = calculate_adx(df)

    df["VOL_SMA20"] = calculate_volume_sma(df)

    df["SUPPORT"], df["RESISTANCE"] = calculate_support_resistance(df)

    df["CANDLE_PATTERN"] = detect_candle_pattern(df)

    # New professional indicators enter the research DataFrame through the
    # registry. Existing indicators stay on their verified legacy path above.
    for name, settings in indicators.items():
        normalized = str(name).strip().lower().replace(" ", "_")
        if normalized in LEGACY_ENGINE_INDICATORS or not settings.get("enabled", False):
            continue
        params = {key: value for key, value in settings.items() if key != "enabled"}
        _attach_registry_output(
            df,
            normalized,
            indicator_registry.calculate(normalized, df, params),
        )

    return df
