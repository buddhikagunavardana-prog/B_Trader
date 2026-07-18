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

MULTI_OUTPUT_COLUMNS = {
    "stochastic": ["STOCHASTIC_K", "STOCHASTIC_D"],
    "stochastic_rsi": ["STOCHASTIC_RSI_K", "STOCHASTIC_RSI_D"],
    "keltner_channel": ["KELTNER_UPPER", "KELTNER_MIDDLE", "KELTNER_LOWER"],
    "donchian_channel": ["DONCHIAN_UPPER", "DONCHIAN_MIDDLE", "DONCHIAN_LOWER"],
    "aroon": ["AROON_UP", "AROON_DOWN"],
    "vortex": ["VORTEX_POSITIVE", "VORTEX_NEGATIVE"],
    "dmi": ["DMI_PLUS", "DMI_MINUS"],
    "elder_ray_index": ["BULL_POWER", "BEAR_POWER"],
    "price_channels": ["PRICE_CHANNEL_UPPER", "PRICE_CHANNEL_MIDDLE", "PRICE_CHANNEL_LOWER"],
    "linear_regression_channel": ["LINEAR_REGRESSION_UPPER", "LINEAR_REGRESSION_MIDDLE", "LINEAR_REGRESSION_LOWER"],
    "ichimoku_cloud": ["ICHIMOKU_CONVERSION", "ICHIMOKU_BASE", "ICHIMOKU_SPAN_A", "ICHIMOKU_SPAN_B", "ICHIMOKU_LAGGING"],
    "parabolic_sar": ["PARABOLIC_SAR", "PARABOLIC_SAR_DIRECTION"],
    "moving_average_envelope": ["MA_ENVELOPE_UPPER", "MA_ENVELOPE_MIDDLE", "MA_ENVELOPE_LOWER"],
    "ppo": ["PPO", "PPO_SIGNAL", "PPO_HISTOGRAM"],
    "chandelier_exit": ["CHANDELIER_LONG", "CHANDELIER_SHORT"],
    "breakout_detection": ["BREAKOUT_UPPER", "BREAKOUT_LOWER", "BREAKOUT_BULLISH", "BREAKOUT_BEARISH"],
    "fair_value_gap": ["FVG_BULLISH", "FVG_BEARISH", "FVG_LOWER", "FVG_UPPER"],
    "order_block": ["ORDER_BLOCK_BULLISH", "ORDER_BLOCK_BEARISH", "ORDER_BLOCK_LOWER", "ORDER_BLOCK_UPPER"],
    "market_structure": ["BOS", "CHOCH", "MARKET_STRUCTURE_TREND"],
    "kst": ["KST", "KST_SIGNAL"],
    "smi_ergodic": ["SMI_ERGODIC", "SMI_ERGODIC_SIGNAL"],
    "relative_vigor_index": ["RELATIVE_VIGOR", "RELATIVE_VIGOR_SIGNAL"],
    "stochastic_momentum_index": ["STOCHASTIC_MOMENTUM", "STOCHASTIC_MOMENTUM_SIGNAL"],
    "volatility_stop": ["VOLATILITY_STOP_LONG", "VOLATILITY_STOP_SHORT"],
    "atr_bands": ["ATR_UPPER_BAND", "ATR_MIDDLE_BAND", "ATR_LOWER_BAND"],
    "fractal_chaos_bands": ["FRACTAL_CHAOS_UPPER", "FRACTAL_CHAOS_LOWER"],
    "moving_std_channel": ["MOVING_STD_UPPER", "MOVING_STD_MIDDLE", "MOVING_STD_LOWER"],
    "klinger_oscillator": ["KLINGER_OSCILLATOR", "KLINGER_SIGNAL"],
    "volume_weighted_macd": ["VOLUME_WEIGHTED_MACD", "VOLUME_WEIGHTED_MACD_SIGNAL", "VOLUME_WEIGHTED_MACD_HISTOGRAM"],
    "wavetrend_oscillator": ["WAVETREND", "WAVETREND_SIGNAL"],
    "squeeze_momentum": ["SQUEEZE_MOMENTUM", "SQUEEZE_ON"],
    "inverse_fair_value_gap": ["INVERSE_FVG_BULLISH", "INVERSE_FVG_BEARISH", "INVERSE_FVG_LOWER", "INVERSE_FVG_UPPER"],
    "liquidity_sweep": ["LIQUIDITY_SWEEP_HIGH", "LIQUIDITY_SWEEP_LOW", "LIQUIDITY_SWEEP_LEVEL"],
    "equal_highs": ["EQUAL_HIGHS", "EQUAL_HIGH_LEVEL"],
    "equal_lows": ["EQUAL_LOWS", "EQUAL_LOW_LEVEL"],
    "breaker_block": ["BREAKER_BLOCK_BULLISH", "BREAKER_BLOCK_BEARISH", "BREAKER_BLOCK_LOWER", "BREAKER_BLOCK_UPPER"],
    "pivot_points": ["PIVOT", "PIVOT_R1", "PIVOT_R2", "PIVOT_R3", "PIVOT_S1", "PIVOT_S2", "PIVOT_S3"],
    "swing_high_low": ["SWING_HIGH", "SWING_LOW"],
}


def _attach_registry_output(df, name, output):
    if isinstance(output, tuple):
        columns = MULTI_OUTPUT_COLUMNS.get(name, [])
        for index, item in enumerate(output, start=1):
            column = columns[index - 1] if index <= len(columns) else f"{name.upper()}_{index}"
            df[column] = item
    elif isinstance(output, dict):
        prefix = name.upper()
        for key, item in output.items():
            column = item.name if item.name else f"{prefix}_{key}"
            df[column] = item
    elif hasattr(output, "columns"):
        for column in output.columns:
            df[column] = output[column]
    else:
        column = output.name if output.name and output.name not in df.columns else name.upper()
        df[column] = output

def calculate_indicators(df, strategy):

    indicators = strategy.indicators

    configured_canonical = set()
    for configured_name, configured_settings in indicators.items():
        if not configured_settings.get("enabled", False):
            continue
        configured = str(configured_name).strip().lower().replace(" ", "_")
        canonical = indicator_registry.get(configured)["name"]
        if canonical in configured_canonical:
            raise ValueError(
                f"duplicate canonical indicator configuration: {canonical}",
            )
        configured_canonical.add(canonical)

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
        canonical = indicator_registry.get(normalized)["name"]
        params = {key: value for key, value in settings.items() if key != "enabled"}
        _attach_registry_output(
            df,
            canonical,
            indicator_registry.calculate(canonical, df, params),
        )

    return df
