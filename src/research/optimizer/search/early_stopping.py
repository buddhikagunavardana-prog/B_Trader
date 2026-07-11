from dataclasses import dataclass


@dataclass
class EarlyStoppingController:
    enabled: bool = False
    patience: int = 20
    minimum_improvement: float = 0.1
    maximum_failures: int = 10
    hard_task_budget: int | None = None
    hard_runtime_budget_seconds: float | None = None

    def __post_init__(self):
        self.reset()

    def reset(self) -> None:
        self.best_score = None
        self.non_improving_count = 0
        self.failure_count = 0
        self.update_count = 0
        self.reason = ""

    def update(
        self,
        score: float | None,
        success: bool = True,
        elapsed_seconds: float | None = None,
    ) -> None:
        if not self.enabled:
            return

        self.update_count += 1

        if self.hard_task_budget is not None and self.update_count >= self.hard_task_budget:
            self.reason = "hard task budget reached"
            return

        if (
            self.hard_runtime_budget_seconds is not None
            and elapsed_seconds is not None
            and elapsed_seconds >= self.hard_runtime_budget_seconds
        ):
            self.reason = "hard runtime budget reached"
            return

        if not success:
            self.failure_count += 1
            if self.failure_count >= self.maximum_failures:
                self.reason = "maximum failed evaluations reached"
            return

        if score is None:
            return

        if self.best_score is None:
            self.best_score = float(score)
            self.non_improving_count = 0
            return

        improvement = float(score) - self.best_score
        if improvement >= self.minimum_improvement:
            self.best_score = float(score)
            self.non_improving_count = 0
            return

        self.non_improving_count += 1
        if self.non_improving_count >= self.patience:
            self.reason = "maximum consecutive non-improving evaluations reached"

    def should_stop(self) -> bool:
        return bool(self.enabled and self.reason)

    def get_reason(self) -> str:
        return self.reason
