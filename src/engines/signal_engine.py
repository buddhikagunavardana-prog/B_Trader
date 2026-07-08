def _has_column(df, column):
    return column in df.columns


def _ema_condition(df, strategy):
    ema = strategy.indicators.get("ema", {})

    if not ema.get("enabled", False):
        return None

    fast = ema.get("fast", 20)
    slow = ema.get("slow", 50)
    trend = ema.get("trend", 200)

    fast_col = f"EMA{fast}"
    slow_col = f"EMA{slow}"
    trend_col = f"EMA{trend}"

    if not all(_has_column(df, col) for col in [fast_col, slow_col, trend_col]):
        return None

    condition = df[fast_col] > df[slow_col]

    if strategy.entry_rules.get("ema200_filter", False):
        condition = condition & (df["close"] > df[trend_col])

    return condition


def _rsi_condition(df, strategy):
    rsi = strategy.indicators.get("rsi", {})

    if not rsi.get("enabled", False):
        return None

    period = rsi.get("period", 14)
    buy_level = rsi.get("buy", 55)
    rsi_col = f"RSI{period}"

    if not _has_column(df, rsi_col):
        return None

    return df[rsi_col] > buy_level


def _macd_condition(df, strategy):
    macd = strategy.indicators.get("macd", {})

    if not macd.get("enabled", False):
        return None

    if not all(_has_column(df, col) for col in ["MACD", "MACD_SIGNAL"]):
        return None

    return df["MACD"] > df["MACD_SIGNAL"]


def _bollinger_condition(df, strategy):
    bollinger = strategy.indicators.get("bollinger", {})

    if not bollinger.get("enabled", False):
        return None

    if not all(_has_column(df, col) for col in ["BB_LOWER", "BB_MIDDLE"]):
        return None

    return df["close"] > df["BB_LOWER"]


def _volume_condition(df, strategy):
    volume = strategy.indicators.get("volume", {})

    if not volume.get("enabled", False):
        return None

    if not all(_has_column(df, col) for col in ["volume", "VOL_SMA20"]):
        return None

    multiplier = volume.get("multiplier", 1.2)

    return df["volume"] > (df["VOL_SMA20"] * multiplier)


def _candlestick_condition(df, strategy):
    candlestick = strategy.indicators.get("candlestick", {})

    if not candlestick.get("enabled", False):
        return None

    if not _has_column(df, "CANDLE_PATTERN"):
        return None

    return df["CANDLE_PATTERN"] != "NONE"


def _supertrend_condition(df, strategy):
    supertrend = strategy.indicators.get("supertrend", {})

    if not supertrend.get("enabled", False):
        return None

    if not _has_column(df, "SUPERTREND_SIGNAL"):
        return None

    return df["SUPERTREND_SIGNAL"] == "BUY"


def generate_signals(df, strategy):
    df["SIGNAL"] = "HOLD"

    conditions = []

    if (
        strategy.entry_rules.get("ema_cross", False)
        or strategy.entry_rules.get("ema200_filter", False)
    ):
        condition = _ema_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("rsi_filter", False):
        condition = _rsi_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("macd_confirmation", False):
        condition = _macd_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("bollinger_reversal", False):
        condition = _bollinger_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("volume_confirmation", False):
        condition = _volume_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("candlestick_confirmation", False):
        condition = _candlestick_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if strategy.entry_rules.get("supertrend_confirmation", False):
        condition = _supertrend_condition(df, strategy)
        if condition is not None:
            conditions.append(condition)

    if len(conditions) == 0:
        return df

    buy_condition = conditions[0]

    for condition in conditions[1:]:
        buy_condition = buy_condition & condition

    df.loc[buy_condition, "SIGNAL"] = "BUY"

    return df