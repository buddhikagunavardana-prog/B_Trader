"""
B Trader Strategy Schema

Supports multiple strategy formats.

Schema Versions

v1
Current strategy.json

v2
Rule Based Strategy Engine

Future:
v3
AI Generated Strategies
"""

SUPPORTED_SCHEMAS = [
    "1.0",
    "2.0",
]

DEFAULT_SCHEMA = "1.0"


def is_supported(schema: str) -> bool:
    return schema in SUPPORTED_SCHEMAS


# ------------------------------------------------------------------
# Phase 18.4 Validation
# ------------------------------------------------------------------

REQUIRED_KEYS = [
    "schema",
    "schema_version",
    "name",
    "version",
    "exchange",
    "market_type",
    "quote_asset",
    "timeframe",
    "symbols",
    "indicators",
    "entry_rules",
    "exit_rules",
    "risk",
    "signal_scoring",
    "research",
]


REQUIRED_RESEARCH_KEYS = [
    "enabled",
    "initial_balance",
    "min_profit_factor",
    "min_trades",
    "max_drawdown_pct",
    "top_n",
]


def validate_strategy_config(config: dict) -> bool:

    if not isinstance(config, dict):
        raise ValueError("Strategy config must be a dictionary")

    for key in REQUIRED_KEYS:
        if key not in config:
            raise ValueError(f"Missing config key: {key}")

    if not is_supported(config["schema"]):
        raise ValueError(
            f"Unsupported schema version: {config['schema']}"
        )

    research = config["research"]

    for key in REQUIRED_RESEARCH_KEYS:
        if key not in research:
            raise ValueError(
                f"Missing research key: {key}"
            )

    if not isinstance(config["symbols"], list):
        raise ValueError("symbols must be a list")

    if len(config["symbols"]) == 0:
        raise ValueError("symbols cannot be empty")

    return True