import json
from pathlib import Path


CONFIG_PATH = Path("src/config/professional_strategy_portfolio.json")


def load_professional_portfolio_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def strategies_for_regime(regime: str, config: dict | None = None) -> list[str]:
    config = config or load_professional_portfolio_config()
    normalized = str(regime).strip().upper()
    route = config["regime_routing"].get(
        normalized,
        config["regime_routing"]["UNKNOWN"],
    )
    return list(route["enabled_strategies"])
