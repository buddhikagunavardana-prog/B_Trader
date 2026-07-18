from src.research.frameworks.profiling.validation import evaluate_budget


def test_framework_performance_budgets():
    assert evaluate_budget(2.0, 10.2, 0, 9.8)["status"] == "PASS"
    assert evaluate_budget(4.0, 10.2, 0, 9.8)["status"] == "WARN"
    assert evaluate_budget(6.0, 10.2, 0, 9.8)["status"] == "WARN"
    assert evaluate_budget(11.0, 13.0, 1, 9.8)["status"] == "BLOCK"


if __name__ == "__main__":
    test_framework_performance_budgets(); print("test_framework_performance_budgets passed")
