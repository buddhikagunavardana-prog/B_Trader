import itertools
from abc import ABC, abstractmethod
from typing import Callable

from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.optimizer.optimizer_constraints import (
    ConstraintResult,
    validate_optimizer_parameters,
)
from src.research.optimizer.optimizer_context import OptimizerContext
from src.research.optimizer.optimizer_space import OptimizationSpace
from src.research.optimizer.search.early_stopping import EarlyStoppingController
from src.research.optimizer.search.search_result import SearchResult
from src.strategies.template_registry import StrategyTemplateRegistry


class BaseSearch(ABC):
    algorithm = "base"

    def __init__(
        self,
        context: OptimizerContext,
        parameter_space: OptimizationSpace,
        optimization_budget: int | None = None,
        deterministic_seed: int | None = None,
        constraint_validator: Callable[[dict], ConstraintResult] | None = None,
        existing_candidate_ids: set[str] | None = None,
        early_stopping_controller: EarlyStoppingController | None = None,
    ):
        self.context = context
        self.parameter_space = parameter_space
        self.optimization_budget = int(
            optimization_budget
            if optimization_budget is not None
            else context.optimization_budget
        )
        self.deterministic_seed = int(
            deterministic_seed
            if deterministic_seed is not None
            else context.random_seed
        )
        self.constraint_validator = constraint_validator or validate_optimizer_parameters
        self.existing_candidate_ids = set(existing_candidate_ids or set())
        self.early_stopping_controller = early_stopping_controller
        self.registry = StrategyTemplateRegistry()
        self.selected_candidates = []
        self.rejected_count = 0
        self.duplicate_count = 0
        self.attempt_count = 0
        self.exhausted = False
        self.stop_reason = ""

    def _iter_template_parameters(self):
        for template_space in self.parameter_space.templates:
            parameter_set = template_space.to_parameter_set()
            parameters = parameter_set["parameters"]
            keys = sorted(parameters)
            values = [parameters[key] for key in keys]

            for combination in itertools.product(*values):
                candidate_parameters = dict(zip(keys, combination))
                candidate_parameters["template_id"] = template_space.template_id
                candidate_parameters["timeframe"] = self.context.timeframe
                yield template_space, candidate_parameters

    def _build_candidate(
        self,
        template_space,
        parameters: dict,
        validation: ConstraintResult,
    ) -> OptimizationCandidate:
        strategy_config = self.registry.build_strategy_config({
            "template_name": template_space.template_name,
            "parameters": parameters,
        })

        return OptimizationCandidate.create(
            strategy_id=strategy_config["strategy_id"],
            template_type=template_space.template_name,
            parameters=parameters,
            validation=validation,
            optimization_metadata={
                "space": self.parameter_space.source,
                "template_id": template_space.template_id,
            },
        )

    def _accept_candidate(self, candidate: OptimizationCandidate) -> bool:
        if (
            candidate.candidate_id in self.existing_candidate_ids
            or candidate.candidate_hash in self.existing_candidate_ids
        ):
            self.duplicate_count += 1
            return False

        self.existing_candidate_ids.add(candidate.candidate_id)
        self.existing_candidate_ids.add(candidate.candidate_hash)
        self.selected_candidates.append(candidate)
        return True

    def _budget_reached(self) -> bool:
        requested = min(self.context.max_candidates, self.optimization_budget)
        return len(self.selected_candidates) >= requested

    def prepare_candidates(self) -> list[OptimizationCandidate]:
        return self.select_candidates()

    @abstractmethod
    def select_candidates(self) -> list[OptimizationCandidate]:
        raise NotImplementedError

    def run(self) -> tuple[list[OptimizationCandidate], SearchResult]:
        candidates = self.prepare_candidates()
        result = SearchResult(
            algorithm=self.algorithm,
            seed=self.deterministic_seed,
            requested_budget=min(self.context.max_candidates, self.optimization_budget),
            selected_count=len(candidates),
            rejected_count=self.rejected_count,
            duplicate_count=self.duplicate_count,
            attempt_count=self.attempt_count,
            exhausted=self.exhausted,
            early_stopped=bool(
                self.early_stopping_controller
                and self.early_stopping_controller.should_stop()
            ),
            stop_reason=self.stop_reason,
            candidate_ids=[candidate.candidate_id for candidate in candidates],
            metadata={
                "space": self.parameter_space.source,
                "template_count": len(self.parameter_space.templates),
            },
        )

        return candidates, result

    def get_state(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "seed": self.deterministic_seed,
            "selected_candidate_ids": [
                candidate.candidate_id
                for candidate in self.selected_candidates
            ],
            "rejected_count": self.rejected_count,
            "duplicate_count": self.duplicate_count,
            "attempt_count": self.attempt_count,
            "exhausted": self.exhausted,
            "stop_reason": self.stop_reason,
        }
