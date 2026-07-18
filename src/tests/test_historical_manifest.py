import json,tempfile
from pathlib import Path
from src.tests.historical_test_data import historical_case

def test_historical_manifest():
    with tempfile.TemporaryDirectory() as root:
        plan,result,_,_,_,_=historical_case("ema_ribbon_trend",80,40,root);manifest=json.loads((Path(result.run_directory)/"manifest.json").read_text(encoding="utf-8"))
        assert manifest["run_id"]==plan.run_id and manifest["status"]=="completed" and len(manifest["completed_chunks"])==2
        assert "code_fingerprint" in manifest and "source_fingerprints" in manifest and "chunks" in manifest
if __name__=="__main__":test_historical_manifest();print("test_historical_manifest passed")
