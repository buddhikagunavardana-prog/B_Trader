import tempfile
from src.tests.historical_test_data import historical_case
from src.trading_frameworks.registry import trading_framework_registry

def test_historical_all_50_compatibility():
    with tempfile.TemporaryDirectory() as root:
        names=trading_framework_registry.list_names();assert len(names)==50
        for name in names:
            plan,result,merged,_,chunked,_=historical_case(name,60,30,root,run_name=f"all35_{name}")
            assert result.completed_chunks==2 and merged.row_count==60 and len(chunked)==60
if __name__=="__main__":test_historical_all_50_compatibility();print("test_historical_all_35_compatibility passed")
