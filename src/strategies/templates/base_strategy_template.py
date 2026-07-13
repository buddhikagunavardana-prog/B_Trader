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
        if self.parameters.get("exit_mode") == "atr_full_position":
            rules = {
                "simulated_exit_mode": "atr_full_position",
                "atr_period": int(self.parameters["atr_exit_period"]),
                "atr_stop_multiplier": float(
                    self.parameters["atr_stop_multiplier"]
                ),
                "atr_target_multiplier": float(
                    self.parameters["atr_target_multiplier"]
                ),
            }
            for key in ("min_stop_percent", "max_stop_percent"):
                value = self.parameters.get(key)
                if value is not None:
                    rules[key] = float(value)
            return rules

        return {
            "simulated_exit_mode": "fixed_percent_full_position",
            "stop_loss_percent": self.parameters["stop_loss_pct"],
            "take_profit_percent": self.parameters["take_profit_pct"],
        }

    def build_risk(self) -> dict:
        if self.parameters.get("position_sizing_mode") == "risk_normalized":
            return {
                "position_sizing_mode": "risk_normalized",
                "risk_per_trade_fraction": float(
                    self.parameters["risk_per_trade_fraction"]
                ),
                "max_capital_allocation_fraction": float(
                    self.parameters["max_capital_allocation_fraction"]
                ),
                "leverage_allowed": bool(
                    self.parameters.get("leverage_allowed", False)
                ),
                "risk_per_trade": (
                    float(self.parameters["risk_per_trade_fraction"])
                    * 100
                ),
            }
        return {
            "position_sizing_mode": "full_allocation",
            "risk_per_trade": self.parameters.get("risk_per_trade", 2),
        }

    def build_config(self) -> dict:
        strategy_id = self.build_strategy_id()
        name = self.build_name()
        indicators = self.build_indicators()
        if self.parameters.get("exit_mode") == "atr_full_position":
            period = int(self.parameters["atr_exit_period"])
            indicators = dict(indicators)
            indicators["atr"] = {
                "enabled": True,
                "period": period,
            }
            strategy_id = (
                f"{strategy_id}_ATREXIT{period}_"
                f"S{self._safe_id_part(self.parameters['atr_stop_multiplier'])}_"
                f"T{self._safe_id_part(self.parameters['atr_target_multiplier'])}"
            )
            name = f"{name} ATR Exit {period}"
        if self.parameters.get("position_sizing_mode") == "risk_normalized":
            risk_pct = (
                float(self.parameters["risk_per_trade_fraction"])
                * 100
            )
            cap_pct = (
                float(self.parameters["max_capital_allocation_fraction"])
                * 100
            )
            strategy_id = (
                f"{strategy_id}_RISK{self._safe_id_part(risk_pct)}_"
                f"CAP{self._safe_id_part(cap_pct)}"
            )
            name = f"{name} Risk {risk_pct:g}% Cap {cap_pct:g}%"

        return {
            "strategy_id": strategy_id,
            "name": name,
            "timeframe": self.parameters.get("timeframe", "15m"),
            "indicators": indicators,
            "entry_rules": self.build_entry_rules(),
            "exit_rules": self.build_exit_rules(),
            "risk": self.build_risk(),
            "enabled": True,
            "template": self.template_name,
            "parameters": self.parameters,
        }
