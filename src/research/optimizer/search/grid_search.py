from src.research.optimizer.search.base_search import BaseSearch


class GridSearch(BaseSearch):
    algorithm = "grid"

    def select_candidates(self):
        for template_space, parameters in self._iter_template_parameters():
            if self._budget_reached():
                self.stop_reason = "budget reached"
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

        return self.selected_candidates
