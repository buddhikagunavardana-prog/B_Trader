import json
from src.research.frameworks.manifest import build_reproducibility_manifest
from src.research.frameworks.preparation import prepare_timeframe_data
from src.tests.framework_expansion_test_data import config,data
from src.trading_frameworks.loader import load_trading_framework
def test_manifest_snapshot_is_json_safe_and_separates_runtime():
 c=config("macd_momentum"); f=load_trading_framework(c.framework); p=prepare_timeframe_data(c,f,data(c.framework)); a=build_reproducibility_manifest(c,f,p); b=build_reproducibility_manifest(c,f,p); assert a["deterministic"]==b["deterministic"] and a["deterministic_hash"]==b["deterministic_hash"] and "decisions" not in a; json.dumps(a)
if __name__=="__main__":test_manifest_snapshot_is_json_safe_and_separates_runtime();print("test_framework_reproducibility_manifest passed")
