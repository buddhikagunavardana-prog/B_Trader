import pandas as pd
from src.research.frameworks.profiling.validation import multi_cutoff_causality_report


def test_framework_optimization_causality():
    report = multi_cutoff_causality_report(120)
    assert len(report) == 50 and report["Causal"].all() and report["Non-Mutating"].all()
    saved = pd.read_csv("reports/framework_optimization_causality.csv")
    assert len(saved) == 35 and saved["Result"].eq("Pass").all() and saved["Cutoffs Tested"].eq(2).all()


if __name__ == "__main__":
    test_framework_optimization_causality(); print("test_framework_optimization_causality passed")
