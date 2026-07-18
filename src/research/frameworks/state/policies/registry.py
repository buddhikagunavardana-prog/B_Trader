from src.research.frameworks.state.policies.framework_policies import framework_policy_requirements


class PolicyRegistry:
    version = "1.0.0"

    def requirements(self, framework: str) -> dict[str, bool]:
        return framework_policy_requirements(framework)


policy_registry = PolicyRegistry()
