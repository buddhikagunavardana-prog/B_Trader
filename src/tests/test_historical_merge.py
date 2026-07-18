import tempfile
from pathlib import Path
import pandas as pd
from src.tests.historical_test_data import historical_case

def test_historical_merge():
    with tempfile.TemporaryDirectory() as root:
        plan,result,merged,_,chunked,_=historical_case("ema_ribbon_trend",137,31,root)
        assert merged.row_count==137 and len(chunked)==137 and not chunked["timestamp"].duplicated().any()
        manifest=Path(result.run_directory)/"merge_manifest.json";assert manifest.exists()
if __name__=="__main__":test_historical_merge();print("test_historical_merge passed")
