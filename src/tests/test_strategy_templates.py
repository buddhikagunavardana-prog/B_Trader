from src.strategies.parameter_generator import ParameterGenerator
from src.strategies.strategy_factory import create_strategy_from_json_config
from src.strategies.template_registry import StrategyTemplateRegistry


def test_unknown_template_rejected():
    registry = StrategyTemplateRegistry()

    try:
        registry.get_template_class("unknown_template")
    except ValueError as error:
        assert "Unknown strategy template" in str(error)
    else:
        raise AssertionError("Unknown template did not fail")


def test_template_builds_valid_strategy_config():
    generator = ParameterGenerator()
    candidate = generator.generate_candidates_for_template("trend")[0]
    config = candidate["config"]

    assert config["strategy_id"].startswith("TRD001")
    assert config["timeframe"] == "15m"
    assert config["enabled"] is True
    assert "ema" in config["indicators"]
    assert "rsi" in config["indicators"]
    assert config["entry_rules"]["ema_cross"] is True


def test_factory_builds_generated_candidate():
    generator = ParameterGenerator()
    candidate = generator.generate_candidates_for_template("trend")[0]
    strategy = create_strategy_from_json_config(candidate["config"])

    assert strategy.name.startswith("Generated Trend")
    assert strategy.timeframe == "15m"
    assert strategy.indicators["ema"]["enabled"] is True
    assert strategy.entry_rules["ema_cross"] is True


def test_generated_candidates_use_project_import_architecture():
    generator = ParameterGenerator()
    candidates = generator.generate_candidates(global_max_candidates=30)

    assert len(candidates) == 30
    assert all(candidate["config"]["enabled"] for candidate in candidates)


if __name__ == "__main__":
    test_unknown_template_rejected()
    test_template_builds_valid_strategy_config()
    test_factory_builds_generated_candidate()
    test_generated_candidates_use_project_import_architecture()
    print("test_strategy_templates passed")
