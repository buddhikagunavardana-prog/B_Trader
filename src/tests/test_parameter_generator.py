from pathlib import Path
import tempfile

from src.strategies.json_strategy_loader import load_enabled_json_strategies
from src.strategies.parameter_generator import ParameterGenerator


def _write_json(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_parameter_sets():
    generator = ParameterGenerator()
    parameter_sets = generator.load_parameter_sets()

    assert len(parameter_sets) == 6
    assert [item["template_name"] for item in parameter_sets] == [
        "breakout",
        "hybrid",
        "mean_reversion",
        "pullback",
        "trend",
        "volume",
    ]


def test_deterministic_candidate_generation():
    generator = ParameterGenerator()
    first = generator.generate_candidates(global_max_candidates=30)
    second = generator.generate_candidates(global_max_candidates=30)

    first_ids = [candidate["strategy_id"] for candidate in first]
    second_ids = [candidate["strategy_id"] for candidate in second]

    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids))


def test_deterministic_atr_exit_variants_preserve_fixed_baseline():
    variant_config = {
        "enabled": True,
        "variants": [{
            "atr_period": 14,
            "stop_multiplier": 1.5,
            "target_multiplier": 3.0,
            "min_stop_percent": 0.75,
            "max_stop_percent": 3.0,
        }],
    }
    generator = ParameterGenerator()
    baseline = generator.generate_candidates(global_max_candidates=30)
    first = generator.generate_candidates(
        global_max_candidates=60,
        atr_exit_variants=variant_config,
    )
    second = generator.generate_candidates(
        global_max_candidates=60,
        atr_exit_variants=variant_config,
    )

    assert [item["strategy_id"] for item in first] == [
        item["strategy_id"] for item in second
    ]
    assert [item["strategy_id"] for item in first[:30]] == [
        item["strategy_id"] for item in baseline
    ]
    assert len(first) == 60
    assert all(
        item["config"]["exit_rules"]["simulated_exit_mode"]
        == "atr_full_position"
        for item in first[30:]
    )
    assert all("ATREXIT14_S1P5_T3P0" in item["strategy_id"] for item in first[30:])


def test_deterministic_risk_variants_cover_fixed_and_atr_exits():
    atr_config = {
        "enabled": True,
        "variants": [{
            "atr_period": 14,
            "stop_multiplier": 1.5,
            "target_multiplier": 3.0,
            "min_stop_percent": 0.75,
            "max_stop_percent": 3.0,
        }],
    }
    risk_config = {
        "enabled": True,
        "variants": [{
            "risk_per_trade_fraction": 0.01,
            "max_capital_allocation_fraction": 0.25,
            "leverage_allowed": False,
        }],
    }
    generator = ParameterGenerator()
    first = generator.generate_candidates(
        global_max_candidates=120,
        atr_exit_variants=atr_config,
        risk_sizing_variants=risk_config,
    )
    second = generator.generate_candidates(
        global_max_candidates=120,
        atr_exit_variants=atr_config,
        risk_sizing_variants=risk_config,
    )

    assert len(first) == 120
    assert [item["strategy_id"] for item in first] == [
        item["strategy_id"] for item in second
    ]
    assert all(
        item["config"]["risk"]["position_sizing_mode"]
        == "full_allocation"
        for item in first[:60]
    )
    assert all(
        item["config"]["risk"]["position_sizing_mode"]
        == "risk_normalized"
        for item in first[60:]
    )
    assert sum(
        item["config"]["exit_rules"]["simulated_exit_mode"]
        == "atr_full_position"
        for item in first[60:]
    ) == 30


def test_max_candidates_enforced():
    generator = ParameterGenerator()
    candidates = generator.generate_candidates_for_template("trend")

    assert len(candidates) == 5


def test_invalid_fast_slow_ema_rejected():
    with tempfile.TemporaryDirectory() as temp_dir:
        parameter_dir = Path(temp_dir)
        _write_json(
            parameter_dir / "trend.json",
            """
            {
                "template_name": "trend",
                "template_id": "TRD999",
                "enabled": true,
                "max_candidates": 5,
                "parameters": {
                    "fast_ema": [200],
                    "slow_ema": [50],
                    "rsi_period": [14],
                    "rsi_pullback": [40],
                    "stop_loss_pct": [1.0],
                    "take_profit_pct": [2.0]
                }
            }
            """,
        )

        generator = ParameterGenerator(parameters_dir=parameter_dir)
        candidates = generator.generate_candidates_for_template("trend")

        assert candidates == []


def test_invalid_parameter_json_fails_clearly():
    with tempfile.TemporaryDirectory() as temp_dir:
        parameter_dir = Path(temp_dir)
        _write_json(
            parameter_dir / "trend.json",
            """
            {
                "template_name": "trend",
                "enabled": true
            }
            """,
        )

        generator = ParameterGenerator(parameters_dir=parameter_dir)

        try:
            generator.load_parameter_sets()
        except ValueError as error:
            assert "Missing required field" in str(error)
        else:
            raise AssertionError("Invalid parameter JSON did not fail")


def test_existing_fixed_json_strategies_still_load():
    strategies = load_enabled_json_strategies()

    assert len(strategies) == 10


if __name__ == "__main__":
    test_load_parameter_sets()
    test_deterministic_candidate_generation()
    test_deterministic_atr_exit_variants_preserve_fixed_baseline()
    test_deterministic_risk_variants_cover_fixed_and_atr_exits()
    test_max_candidates_enforced()
    test_invalid_fast_slow_ema_rejected()
    test_invalid_parameter_json_fails_clearly()
    test_existing_fixed_json_strategies_still_load()
    print("test_parameter_generator passed")
