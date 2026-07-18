from src.research.frameworks.reporting import build_performance_report
from src.trading_frameworks.registry import trading_framework_registry
def test_registry_aware_framework_performance_smoke():
 report=build_performance_report((50,),1); assert len(report)==len(trading_framework_registry.list_names()) and (report["Repeated Indicator Calculations"]==0).all()
if __name__=="__main__":test_registry_aware_framework_performance_smoke();print("test_framework_expansion_performance passed")
