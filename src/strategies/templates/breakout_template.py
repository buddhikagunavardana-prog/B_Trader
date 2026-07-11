from src.strategies.templates.base_strategy_template import BaseStrategyTemplate


class BreakoutTemplate(BaseStrategyTemplate):
    template_name = "breakout"
    id_prefix = "BRK"
    display_name = "Breakout"

    def build_strategy_id(self) -> str:
        return (
            f"{self.parameters['template_id']}_"
            f"EMA{self.parameters['fast_ema']}_"
            f"{self.parameters['slow_ema']}_"
            f"ATR{self.parameters['atr_period']}_"
            f"SL{self._safe_id_part(self.parameters['stop_loss_pct'])}_"
            f"TP{self._safe_id_part(self.parameters['take_profit_pct'])}"
        )

    def build_name(self) -> str:
        return (
            "Generated Breakout EMA "
            f"{self.parameters['fast_ema']}/{self.parameters['slow_ema']} "
            f"ATR {self.parameters['atr_period']}"
        )

    def build_indicators(self) -> dict:
        return {
            "ema": {
                "enabled": True,
                "fast": self.parameters["fast_ema"],
                "slow": self.parameters["slow_ema"],
                "trend": self.parameters["slow_ema"],
            },
            "atr": {
                "enabled": True,
                "period": self.parameters["atr_period"],
                "multiplier": self.parameters.get("atr_multiplier", 2),
            },
        }

    def build_entry_rules(self) -> dict:
        return {
            "ema_cross": True,
            "ema200_filter": True,
        }
