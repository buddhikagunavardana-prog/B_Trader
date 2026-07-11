from src.strategies.templates.base_strategy_template import BaseStrategyTemplate


class MeanReversionTemplate(BaseStrategyTemplate):
    template_name = "mean_reversion"
    id_prefix = "MRV"
    display_name = "Mean Reversion"

    def build_strategy_id(self) -> str:
        return (
            f"{self.parameters['template_id']}_"
            f"BB{self.parameters['bollinger_period']}_"
            f"RSI{self.parameters['rsi_period']}_"
            f"BUY{self.parameters['rsi_buy']}_"
            f"SL{self._safe_id_part(self.parameters['stop_loss_pct'])}_"
            f"TP{self._safe_id_part(self.parameters['take_profit_pct'])}"
        )

    def build_name(self) -> str:
        return (
            "Generated Mean Reversion Bollinger "
            f"{self.parameters['bollinger_period']} "
            f"RSI {self.parameters['rsi_buy']}"
        )

    def build_indicators(self) -> dict:
        return {
            "bollinger": {
                "enabled": True,
                "period": self.parameters["bollinger_period"],
                "std_dev": self.parameters["bollinger_std"],
            },
            "rsi": {
                "enabled": True,
                "period": self.parameters["rsi_period"],
                "buy": self.parameters["rsi_buy"],
            },
        }

    def build_entry_rules(self) -> dict:
        return {
            "bollinger_reversal": True,
            "rsi_filter": True,
        }
