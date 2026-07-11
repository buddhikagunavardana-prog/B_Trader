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
    test_max_candidates_enforced()
    test_invalid_fast_slow_ema_rejected()
    test_invalid_parameter_json_fails_clearly()
    test_existing_fixed_json_strategies_still_load()
    print("test_parameter_generator passed")
