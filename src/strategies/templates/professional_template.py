import copy
import hashlib
import json
from pathlib import Path

from src.strategies.templates.base_strategy_template import BaseStrategyTemplate


DEFINITIONS_DIR = Path("src/strategies/definitions")


class ProfessionalDefinitionTemplate(BaseStrategyTemplate):
    definition_filename = ""

    def _definition(self) -> dict:
        path = DEFINITIONS_DIR / self.definition_filename
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def build_strategy_id(self) -> str:
        base = self._definition()["strategy_id"]
        signature = json.dumps(self.parameters, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:10].upper()
        return f"{base}_{digest}"

    def build_name(self) -> str:
        return self._definition()["name"]

    def build_indicators(self) -> dict:
        return copy.deepcopy(self._definition()["indicators"])

    def build_entry_rules(self) -> dict:
        return copy.deepcopy(self._definition()["entry_rules"])

    def build_config(self) -> dict:
        config = copy.deepcopy(self._definition())
        config["strategy_id"] = self.build_strategy_id()
        config["name"] = self.build_name()
        config["enabled"] = True
        config["template"] = self.template_name
        config["parameters"] = copy.deepcopy(self.parameters)
        ema = config["indicators"].get("ema", {})
        for source, target in [("fast_ema", "fast"), ("slow_ema", "slow"), ("structure_ema", "trend")]:
            if source in self.parameters:
                ema[target] = self.parameters[source]
        for source, target in [
            ("donchian_period", "donchian_period"),
            ("adx_threshold", "adx_min"),
            ("rsi_threshold", "previous_rsi_max"),
            ("relative_volume_threshold", "relative_volume_min"),
            ("zscore_threshold", "zscore_max"),
        ]:
            if source in self.parameters:
                config["entry_rules"][target] = self.parameters[source]
        for key in ["stop_loss_pct", "take_profit_pct"]:
            if key in self.parameters:
                config["exit_rules"][key.replace("_pct", "_percent")] = self.parameters[key]
        return config


class ProfessionalMomentumTemplate(ProfessionalDefinitionTemplate):
    template_name = "professional_momentum"
    definition_filename = "professional_time_series_momentum.json"


class ProfessionalBreakoutTemplate(ProfessionalDefinitionTemplate):
    template_name = "professional_breakout"
    definition_filename = "professional_compression_breakout.json"


class ProfessionalPullbackTemplate(ProfessionalDefinitionTemplate):
    template_name = "professional_pullback"
    definition_filename = "professional_trend_pullback.json"


class ProfessionalMeanReversionTemplate(ProfessionalDefinitionTemplate):
    template_name = "professional_mean_reversion"
    definition_filename = "professional_regime_mean_reversion.json"
