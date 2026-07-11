from src.strategies.templates.breakout_template import BreakoutTemplate
from src.strategies.templates.hybrid_template import HybridTemplate
from src.strategies.templates.mean_reversion_template import MeanReversionTemplate
from src.strategies.templates.pullback_template import PullbackTemplate
from src.strategies.templates.trend_template import TrendTemplate
from src.strategies.templates.volume_template import VolumeTemplate


TEMPLATE_REGISTRY = {
    "trend": TrendTemplate,
    "pullback": PullbackTemplate,
    "breakout": BreakoutTemplate,
    "mean_reversion": MeanReversionTemplate,
    "volume": VolumeTemplate,
    "hybrid": HybridTemplate,
}


class StrategyTemplateRegistry:
    def __init__(self, registry: dict | None = None):
        self.registry = registry or TEMPLATE_REGISTRY

    def get_template_class(self, template_name: str):
        if template_name not in self.registry:
            raise ValueError(f"Unknown strategy template: {template_name}")

        return self.registry[template_name]

    def build_strategy_config(self, candidate: dict) -> dict:
        template_name = candidate["template_name"]
        template_class = self.get_template_class(template_name)
        template = template_class(candidate["parameters"])

        return template.build_config()
