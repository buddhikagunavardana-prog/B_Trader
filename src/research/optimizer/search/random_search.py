import random

from src.research.optimizer.search.base_search import BaseSearch


class RandomSearch(BaseSearch):
    algorithm = "random"

    def __init__(self, *args, max_attempts: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_attempts = int(
            max_attempts
            if max_attempts is not None
            else self.context.max_random_attempts
        )

    def select_candidates(self):
        rng = random.Random(self.deterministic_seed)
        candidate_specs = list(self._iter_template_parameters())
        rng.shuffle(candidate_specs)

        for template_space, parameters in candidate_specs:
            if self._budget_reached():
                self.stop_reason = "budget reached"
                break

            if self.attempt_count >= self.max_attempts:
                self.stop_reason = "maximum random attempts reached"
                break

            self.attempt_count += 1
            validation = self.constraint_validator(parameters)
            if not validation.is_valid and self.context.strict_constraints:
                self.rejected_count += 1
                continue

            candidate = self._build_candidate(template_space, parameters, validation)
            self._accept_candidate(candidate)

            if (
                self.early_stopping_controller
                and self.early_stopping_controller.should_stop()
            ):
                self.stop_reason = self.early_stopping_controller.get_reason()
                break
        else:
            self.exhausted = True
            self.stop_reason = "search space exhausted"

        if not self.stop_reason and self.attempt_count >= self.max_attempts:
            self.stop_reason = "maximum random attempts reached"

        return self.selected_candidates
