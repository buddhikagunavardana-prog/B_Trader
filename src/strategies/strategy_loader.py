import json
from pathlib import Path

from src.strategies.strategy_model import Strategy
from src.strategies.strategy_schema import (
    DEFAULT_SCHEMA,
    is_supported,
    validate_strategy_config,
)
from src.strategies.strategy_validator import validate_strategy


def load_strategy_config(config_path: str = "src/config/strategy.json") -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Strategy config not found: {config_path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    validate_strategy_config(data)
    return data


def load_strategy(config_path: str = "src/config/strategy.json") -> Strategy:
    data = load_strategy_config(config_path)

    schema = data.get("schema", DEFAULT_SCHEMA)

    if not is_supported(schema):
        raise ValueError(
            f"Unsupported strategy schema: {schema}"
        )

    validate_strategy(data)

    return Strategy(
        name=data["name"],
        version=data["version"],
        exchange=data["exchange"],
        market_type=data["market_type"],
        quote_asset=data["quote_asset"],
        symbols=data["symbols"],
        timeframe=data["timeframe"],
        indicators=data["indicators"],
        entry_rules=data["entry_rules"],
        exit_rules=data["exit_rules"],
        risk=data["risk"],
        signal_scoring=data["signal_scoring"],
    )