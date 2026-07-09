import copy

from src.strategies.json_strategy_loader import load_enabled_json_strategies
from src.strategies.strategy_loader import load_strategy


def _base_strategy():
    return load_strategy("src/config/strategy.json")


def _disable_all_indicators(strategy):
    for indicator in strategy.indicators:
        strategy.indicators[indicator]["enabled"] = False


def _disable_all_entry_rules(strategy):
    for rule in strategy.entry_rules:
        strategy.entry_rules[rule] = False


def create_strategy_combination(name, enabled_indicators, enabled_rules):
    strategy = copy.deepcopy(_base_strategy())
    strategy.name = name

    _disable_all_indicators(strategy)
    _disable_all_entry_rules(strategy)

    for indicator in enabled_indicators:
        if indicator in strategy.indicators:
            strategy.indicators[indicator]["enabled"] = True

    for rule in enabled_rules:
        if rule in strategy.entry_rules:
            strategy.entry_rules[rule] = True

    return strategy


def create_strategy_from_json_config(config: dict):
    strategy = copy.deepcopy(_base_strategy())

    strategy.name = config["name"]
    strategy.timeframe = config["timeframe"]

    _disable_all_indicators(strategy)
    _disable_all_entry_rules(strategy)

    for indicator, settings in config["indicators"].items():
        if indicator not in strategy.indicators:
            continue

        strategy.indicators[indicator].update(settings)
        strategy.indicators[indicator]["enabled"] = settings.get("enabled", True)

    for rule, enabled in config["entry_rules"].items():
        if rule in strategy.entry_rules:
            strategy.entry_rules[rule] = bool(enabled)

    strategy.exit_rules.update(config["exit_rules"])
    strategy.risk.update(config["risk"])

    return strategy


def get_json_strategy_combinations():
    return [
        create_strategy_from_json_config(config)
        for config in load_enabled_json_strategies()
    ]


def get_strategy_combinations():
    json_strategies = get_json_strategy_combinations()

    if json_strategies:
        return json_strategies

    return [
        create_strategy_combination(
            name="EMA Trend + RSI Pullback",
            enabled_indicators=["ema", "rsi"],
            enabled_rules=["ema_cross", "ema200_filter", "rsi_filter"],
        ),
        create_strategy_combination(
            name="EMA 200 Filter + MACD Cross",
            enabled_indicators=["ema", "macd"],
            enabled_rules=["ema200_filter", "macd_confirmation"],
        ),
        create_strategy_combination(
            name="Bollinger Band Reversal + RSI",
            enabled_indicators=["bollinger", "rsi"],
            enabled_rules=["bollinger_reversal", "rsi_filter"],
        ),
        create_strategy_combination(
            name="SuperTrend + EMA + ATR SL",
            enabled_indicators=["supertrend", "ema", "atr"],
            enabled_rules=["supertrend_confirmation", "ema200_filter"],
        ),
        create_strategy_combination(
            name="Candlestick Confirmation + Volume",
            enabled_indicators=["candlestick", "volume"],
            enabled_rules=["candlestick_confirmation", "volume_confirmation"],
        ),
        create_strategy_combination(
            name="EMA 20/50 Cross + RSI Filter",
            enabled_indicators=["ema", "rsi"],
            enabled_rules=["ema_cross", "rsi_filter"],
        ),
        create_strategy_combination(
            name="MACD + RSI + Volume",
            enabled_indicators=["macd", "rsi", "volume"],
            enabled_rules=["macd_confirmation", "rsi_filter", "volume_confirmation"],
        ),
        create_strategy_combination(
            name="Bollinger + ATR Volatility Filter",
            enabled_indicators=["bollinger", "atr"],
            enabled_rules=["bollinger_reversal"],
        ),
        create_strategy_combination(
            name="SuperTrend + RSI",
            enabled_indicators=["supertrend", "rsi"],
            enabled_rules=["supertrend_confirmation", "rsi_filter"],
        ),
        create_strategy_combination(
            name="EMA 200 Trend + Candlestick Confirmation",
            enabled_indicators=["ema", "candlestick"],
            enabled_rules=["ema200_filter", "candlestick_confirmation"],
        ),
    ]
