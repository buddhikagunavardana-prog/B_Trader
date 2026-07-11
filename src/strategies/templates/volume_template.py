from src.strategies.templates.base_strategy_template import BaseStrategyTemplate


class VolumeTemplate(BaseStrategyTemplate):
    template_name = "volume"
    id_prefix = "VOL"
    display_name = "Volume"

    def build_strategy_id(self) -> str:
        return (
            f"{self.parameters['template_id']}_"
            f"EMA{self.parameters['fast_ema']}_"
            f"{self.parameters['slow_ema']}_"
            f"VOL{self._safe_id_part(self.parameters['volume_multiplier'])}_"
            f"SL{self._safe_id_part(self.parameters['stop_loss_pct'])}_"
            f"TP{self._safe_id_part(self.parameters['take_profit_pct'])}"
        )

    def build_name(self) -> str:
        return (
            "Generated Volume EMA "
            f"{self.parameters['fast_ema']}/{self.parameters['slow_ema']} "
            f"Vol {self.parameters['volume_multiplier']}"
        )

    def build_indicators(self) -> dict:
        return {
            "ema": {
                "enabled": True,
                "fast": self.parameters["fast_ema"],
                "slow": self.parameters["slow_ema"],
                "trend": self.parameters["slow_ema"],
            },
            "volume": {
                "enabled": True,
                "period": self.parameters["volume_period"],
                "multiplier": self.parameters["volume_multiplier"],
            },
        }

    def build_entry_rules(self) -> dict:
        return {
            "ema_cross": True,
            "volume_confirmation": True,
        }
