from src.research.frameworks.profiling.reporting import write_equivalence_and_causality_reports


def test_framework_output_equivalence():
    equivalence, _ = write_equivalence_and_causality_reports(rows=100)
    assert len(equivalence) == 50 and equivalence["Result"].eq("Pass").all()


if __name__ == "__main__":
    test_framework_output_equivalence(); print("test_framework_output_equivalence passed")
