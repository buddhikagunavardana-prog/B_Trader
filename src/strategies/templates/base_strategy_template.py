import re


class BaseStrategyTemplate:
    template_name = "base"
    id_prefix = "BASE"
    display_name = "Base Strategy Template"

    def __init__(self, parameters: dict):
        self.parameters = parameters

    def _safe_id_part(self, value) -> str:
        text = str(value).replace(".", "P")
        text = re.sub(r"[^A-Za-z0-9]+", "_", text)
        return text.strip("_").upper()

    def build_strategy_id(self) -> str:
        raise NotImplementedError

    def build_name(self) -> str:
        raise NotImplementedError

    def build_indicators(self) -> dict:
        raise NotImplementedError

    def build_entry_rules(self) -> dict:
        raise NotImplementedError

    def build_exit_rules(self) -> dict:
        return {
            "stop_loss_percent": self.parameters["stop_loss_pct"],
            "take_profit_percent": self.parameters["take_profit_pct"],
        }

    def build_risk(self) -> dict:
        return {
            "risk_per_trade": self.parameters.get("risk_per_trade", 2),
        }

    def build_config(self) -> dict:
        return {
            "strategy_id": self.build_strategy_id(),
            "name": self.build_name(),
            "timeframe": self.parameters.get("timeframe", "15m"),
            "indicators": self.build_indicators(),
            "entry_rules": self.build_entry_rules(),
            "exit_rules": self.build_exit_rules(),
            "risk": self.build_risk(),
            "enabled": True,
            "template": self.template_name,
            "parameters": self.parameters,
        }
