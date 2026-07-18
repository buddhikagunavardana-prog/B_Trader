from src.research.frameworks.inventory import build_adapter_inventory
from src.research.frameworks.reporting import build_performance_report, build_validation_report


def test_inventory_validation_and_performance_reports_are_structural_only():
    inventory = build_adapter_inventory(); validation = build_validation_report(60)
    performance = build_performance_report((60,), 1)
    assert len(inventory) == 8 and set(inventory["Status"]) == {"Complete"}
    assert len(validation) == 20 and set(validation["Result"]) == {"Pass"}
    assert len(performance) == 20 and (performance["Repeated Indicator Calculations"] == 0).all()
    banned = {"pnl", "roi", "win rate", "profit factor", "drawdown", "sharpe", "balance"}
    assert not any(term in " ".join(map(str.lower, performance.columns)) for term in banned)


if __name__ == "__main__":
    test_inventory_validation_and_performance_reports_are_structural_only(); print("test_framework_research_reporting passed")
