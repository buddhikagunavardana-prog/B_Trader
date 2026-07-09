import json
from pathlib import Path


DEFINITIONS_DIR = Path("src/strategies/definitions")

REQUIRED_FIELDS = [
    "strategy_id",
    "name",
    "timeframe",
    "indicators",
    "entry_rules",
    "exit_rules",
    "risk",
    "enabled",
]


def validate_json_strategy_config(config: dict, source: Path) -> None:
    if not isinstance(config, dict):
        raise ValueError(f"Strategy definition must be a dictionary: {source}")

    for field in REQUIRED_FIELDS:
        if field not in config:
            raise ValueError(f"Missing required field '{field}' in {source}")

    if not config["strategy_id"]:
        raise ValueError(f"strategy_id cannot be empty in {source}")

    if config["timeframe"] != "15m":
        raise ValueError(f"Only 15m JSON strategies are supported in {source}")

    for field in ["indicators", "entry_rules", "exit_rules", "risk"]:
        if not isinstance(config[field], dict):
            raise ValueError(f"{field} must be a dictionary in {source}")


def load_json_strategy_file(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        config = json.load(file)

    validate_json_strategy_config(config, path)
    return config


def load_enabled_json_strategies(
    definitions_dir: Path = DEFINITIONS_DIR,
) -> list[dict]:
    if not definitions_dir.exists():
        return []

    strategies = []

    for path in sorted(definitions_dir.glob("*.json")):
        config = load_json_strategy_file(path)

        if config.get("enabled", False):
            strategies.append(config)

    return strategies
