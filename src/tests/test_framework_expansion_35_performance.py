from src.research.frameworks.reporting import build_performance_report


def test_35_framework_performance_smoke():
    report = build_performance_report((50,), 1)
    assert len(report) == 35 and (report["Repeated Indicator Calculations"] == 0).all()


if __name__ == "__main__":
    test_35_framework_performance_smoke(); print("test_framework_expansion_35_performance passed")
