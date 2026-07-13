import copy
import itertools
import json
from pathlib import Path

from src.strategies.template_registry import StrategyTemplateRegistry


PARAMETERS_DIR = Path("src/strategies/parameters")
REQUIRED_FIELDS = [
    "template_name",
    "template_id",
    "enabled",
    "max_candidates",
    "parameters",
]


class ParameterGenerator:
    def __init__(
        self,
        parameters_dir: Path = PARAMETERS_DIR,
        registry: StrategyTemplateRegistry | None = None,
    ):
        self.parameters_dir = parameters_dir
        self.registry = registry or StrategyTemplateRegistry()

    def _load_json_file(self, path: Path) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid parameter JSON: {path}: {error}") from error

        self._validate_parameter_set(data, path)
        return data

    def _validate_parameter_set(self, data: dict, source: Path) -> None:
        if not isinstance(data, dict):
            raise ValueError(f"Parameter file must be a dictionary: {source}")

        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in {source}")

        if not isinstance(data["parameters"], dict):
            raise ValueError(f"parameters must be a dictionary in {source}")

        if not isinstance(data["max_candidates"], int):
            raise ValueError(f"max_candidates must be an integer in {source}")

        if data["max_candidates"] <= 0:
            raise ValueError(f"max_candidates must be positive in {source}")

        self.registry.get_template_class(data["template_name"])

    def load_parameter_sets(self) -> list[dict]:
        if not self.parameters_dir.exists():
            return []

        parameter_sets = []

        for path in sorted(self.parameters_dir.glob("*.json")):
            data = self._load_json_file(path)

            if data.get("enabled", False):
                parameter_sets.append(data)

        return parameter_sets

    def _iter_parameter_combinations(self, parameter_set: dict):
        parameters = parameter_set["parameters"]
        keys = sorted(parameters)
        values = []

        for key in keys:
            value = parameters[key]

            if not isinstance(value, list) or not value:
                raise ValueError(
                    f"Parameter '{key}' must be a non-empty list "
                    f"for {parameter_set['template_name']}"
                )

            values.append(value)

        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))
            params["template_id"] = parameter_set["template_id"]
            params["timeframe"] = "15m"
            yield params

    def _is_valid_parameter_combination(self, parameters: dict) -> bool:
        fast_ema = parameters.get("fast_ema")
        slow_ema = parameters.get("slow_ema")

        if fast_ema is not None and slow_ema is not None:
            return int(fast_ema) < int(slow_ema)

        return True

    def validate_candidate(self, candidate: dict) -> None:
        for field in ["strategy_id", "template_name", "parameters", "config"]:
            if field not in candidate:
                raise ValueError(f"Missing candidate field: {field}")

        if not candidate["strategy_id"]:
            raise ValueError("Candidate strategy_id cannot be empty")

        if not self._is_valid_parameter_combination(candidate["parameters"]):
            raise ValueError(
                f"Invalid EMA combination for {candidate['strategy_id']}: "
                "fast_ema must be lower than slow_ema"
            )

    def _build_candidate(self, parameter_set: dict, parameters: dict) -> dict:
        candidate_shell = {
            "template_name": parameter_set["template_name"],
            "parameters": parameters,
        }
        config = self.registry.build_strategy_config(candidate_shell)
        candidate = {
            "strategy_id": config["strategy_id"],
            "template_name": parameter_set["template_name"],
            "parameters": parameters,
            "config": config,
        }
        self.validate_candidate(candidate)

        return candidate

    def generate_candidates_for_template(self, template_name: str) -> list[dict]:
        parameter_sets = [
            parameter_set
            for parameter_set in self.load_parameter_sets()
            if parameter_set["template_name"] == template_name
        ]

        if not parameter_sets:
            raise ValueError(f"No enabled parameter set found for {template_name}")

        candidates = []

        for parameter_set in parameter_sets:
            for parameters in self._iter_parameter_combinations(parameter_set):
                if not self._is_valid_parameter_combination(parameters):
                    continue

                candidates.append(self._build_candidate(parameter_set, parameters))

                if len(candidates) >= parameter_set["max_candidates"]:
                    break

        return candidates

    def generate_candidates(
        self,
        enabled_templates: list[str] | None = None,
        global_max_candidates: int | None = None,
        atr_exit_variants: dict | None = None,
    ) -> list[dict]:
        candidates = []
        seen_ids = set()

        for parameter_set in self.load_parameter_sets():
            template_name = parameter_set["template_name"]

            if enabled_templates and template_name not in enabled_templates:
                continue

            template_candidates = self.generate_candidates_for_template(
                template_name
            )

            for candidate in template_candidates:
                strategy_id = candidate["strategy_id"]

                if strategy_id in seen_ids:
                    raise ValueError(f"Duplicate generated strategy ID: {strategy_id}")

                seen_ids.add(strategy_id)
                candidates.append(candidate)

        if atr_exit_variants and atr_exit_variants.get("enabled", False):
            baseline_candidates = list(candidates)
            for variant in atr_exit_variants.get("variants", []):
                required = {
                    "atr_period",
                    "stop_multiplier",
                    "target_multiplier",
                }
                missing = required.difference(variant)
                if missing:
                    raise ValueError(
                        "ATR exit variant is missing fields: "
                        f"{sorted(missing)}"
                    )
                if any(float(variant[key]) <= 0 for key in required):
                    raise ValueError("ATR exit variant values must be positive")
                minimum = variant.get("min_stop_percent")
                maximum = variant.get("max_stop_percent")
                if minimum is not None and float(minimum) <= 0:
                    raise ValueError("min_stop_percent must be positive")
                if maximum is not None and float(maximum) <= 0:
                    raise ValueError("max_stop_percent must be positive")
                if (
                    minimum is not None
                    and maximum is not None
                    and float(minimum) > float(maximum)
                ):
                    raise ValueError(
                        "min_stop_percent cannot exceed max_stop_percent"
                    )

                for baseline in baseline_candidates:
                    parameters = copy.deepcopy(baseline["parameters"])
                    parameters.update({
                        "exit_mode": "atr_full_position",
                        "atr_exit_period": int(variant["atr_period"]),
                        "atr_stop_multiplier": float(
                            variant["stop_multiplier"]
                        ),
                        "atr_target_multiplier": float(
                            variant["target_multiplier"]
                        ),
                        "min_stop_percent": minimum,
                        "max_stop_percent": maximum,
                    })
                    candidate = self._build_candidate(
                        {"template_name": baseline["template_name"]},
                        parameters,
                    )
                    strategy_id = candidate["strategy_id"]
                    if strategy_id in seen_ids:
                        raise ValueError(
                            f"Duplicate generated strategy ID: {strategy_id}"
                        )
                    seen_ids.add(strategy_id)
                    candidates.append(candidate)

        if global_max_candidates is not None:
            return candidates[:global_max_candidates]

        return candidates
