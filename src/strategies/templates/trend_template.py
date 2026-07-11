from src.strategies.templates.base_strategy_template import BaseStrategyTemplate


class TrendTemplate(BaseStrategyTemplate):
    template_name = "trend"
    id_prefix = "TRD"
    display_name = "Trend"

    def build_strategy_id(self) -> str:
        return (
            f"{self.parameters['template_id']}_"
            f"EMA{self.parameters['fast_ema']}_"
            f"{self.parameters['slow_ema']}_"
            f"RSI{self.parameters['rsi_period']}_"
            f"PB{self.parameters['rsi_pullback']}_"
            f"SL{self._safe_id_part(self.parameters['stop_loss_pct'])}_"
            f"TP{self._safe_id_part(self.parameters['take_profit_pct'])}"
        )

    def build_name(self) -> str:
        return (
            "Generated Trend EMA "
            f"{self.parameters['fast_ema']}/{self.parameters['slow_ema']} "
            f"RSI {self.parameters['rsi_period']}"
        )

    def build_indicators(self) -> dict:
        return {
            "ema": {
                "enabled": True,
                "fast": self.parameters["fast_ema"],
                "slow": self.parameters["slow_ema"],
                "trend": self.parameters["slow_ema"],
            },
            "rsi": {
                "enabled": True,
                "period": self.parameters["rsi_period"],
                "buy": self.parameters["rsi_pullback"],
            },
        }

    def build_entry_rules(self) -> dict:
        return {
            "ema_cross": True,
            "ema200_filter": True,
            "rsi_filter": True,
        }
