from dataclasses import dataclass, field

from src.research.orchestrator.orchestrator_stage import OrchestratorStage


@dataclass(frozen=True)
class OrchestratorPlan:
    stages: list[OrchestratorStage]
    execution_order: list[str]
    estimated_task_count: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stages": [stage.to_dict() for stage in self.stages],
            "execution_order": list(self.execution_order),
            "estimated_task_count": self.estimated_task_count,
            "warnings": list(self.warnings),
        }


def _smoke_stages(context) -> list[str]:
    requested = context.enabled_stages or [
        "load_data",
        "optimization_search",
        "monte_carlo",
    ]
    return requested[:3]


def _apply_overrides(stage: OrchestratorStage, overrides: dict) -> OrchestratorStage:
    if not overrides:
        return stage

    allowed = {
        "enabled",
        "required",
        "dependencies",
        "input_artifacts",
        "output_artifacts",
        "task_budget",
        "runtime_budget_seconds",
        "allow_resume",
        "metadata",
    }
    updates = {key: value for key, value in overrides.items() if key in allowed}
    return stage.with_updates(**updates)


def _topological_sort(stages: dict[str, OrchestratorStage], preferred_order: list[str]):
    ordered = []
    visiting = set()
    visited = set()
    preferred_index = {
        stage_name: index
        for index, stage_name in enumerate(preferred_order)
    }

    def visit(stage_name: str):
        if stage_name in visited:
            return

        if stage_name in visiting:
            raise ValueError(f"Cycle detected at stage: {stage_name}")

        if stage_name not in stages:
            raise ValueError(f"Missing dependency stage: {stage_name}")

        visiting.add(stage_name)
        dependencies = sorted(
            stages[stage_name].dependencies,
            key=lambda item: preferred_index.get(item, 9999),
        )
        for dependency in dependencies:
            visit(dependency)

        visiting.remove(stage_name)
        visited.add(stage_name)
        ordered.append(stage_name)

    for stage_name in sorted(
        stages,
        key=lambda item: preferred_index.get(item, 9999),
    ):
        visit(stage_name)

    return ordered


def build_plan(context, registry: dict[str, OrchestratorStage]) -> OrchestratorPlan:
    requested_stage_names = (
        _smoke_stages(context)
        if context.smoke_mode
        else list(context.enabled_stages)
    )
    selected = {}
    warnings = []

    for stage_name in requested_stage_names:
        if stage_name not in registry:
            raise ValueError(f"Unknown orchestrator stage: {stage_name}")

        stage = _apply_overrides(
            registry[stage_name],
            context.stage_overrides.get(stage_name, {}),
        )
        if stage.enabled:
            selected[stage_name] = stage

    index = 0
    while index < len(list(selected.values())):
        stage = list(selected.values())[index]
        for dependency in stage.dependencies:
            if dependency not in selected:
                if dependency not in registry:
                    raise ValueError(
                        f"Stage {stage.name} depends on unknown stage {dependency}"
                    )
                dependency_stage = _apply_overrides(
                    registry[dependency],
                    context.stage_overrides.get(dependency, {}),
                )
                if dependency_stage.enabled:
                    selected[dependency] = dependency_stage
                else:
                    warnings.append(
                        f"Dependency {dependency} for {stage.name} is disabled"
                    )
        index += 1

    execution_order = _topological_sort(selected, context.stage_order)
    ordered_stages = [selected[name] for name in execution_order]
    estimated_task_count = sum(stage.task_budget or 1 for stage in ordered_stages)
    plan = OrchestratorPlan(
        stages=ordered_stages,
        execution_order=execution_order,
        estimated_task_count=estimated_task_count,
        warnings=warnings,
    )
    validate_plan(plan, context)

    return plan


def validate_plan(plan: OrchestratorPlan, context) -> None:
    if plan.estimated_task_count > context.global_task_budget:
        raise ValueError("Plan estimated task count exceeds global task budget")

    for stage in plan.stages:
        if stage.task_budget is not None and stage.task_budget < 0:
            raise ValueError(f"Stage task budget cannot be negative: {stage.name}")

        if (
            stage.runtime_budget_seconds is not None
            and stage.runtime_budget_seconds < 0
        ):
            raise ValueError(
                f"Stage runtime budget cannot be negative: {stage.name}"
            )


def summarize_plan(plan: OrchestratorPlan) -> dict:
    return {
        "execution_order": list(plan.execution_order),
        "stage_count": len(plan.stages),
        "estimated_task_count": plan.estimated_task_count,
        "stages": [
            {
                "name": stage.name,
                "display_name": stage.display_name,
                "required": stage.required,
                "dependencies": list(stage.dependencies),
                "outputs": list(stage.output_artifacts),
            }
            for stage in plan.stages
        ],
        "warnings": list(plan.warnings),
    }
