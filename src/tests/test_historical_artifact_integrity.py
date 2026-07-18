import tempfile
from pathlib import Path
from src.tests.historical_test_data import historical_case
from src.research.frameworks.historical.exceptions import ArtifactCorruptionError
from src.research.frameworks.historical.integrity import validate_chunk

def test_historical_artifact_integrity():
    with tempfile.TemporaryDirectory() as root:
        plan,result,_,_,_,_=historical_case("ema_ribbon_trend",80,40,root)
        artifact=next((Path(result.run_directory)/"chunks/chunk_000000").glob("decisions*"));artifact.write_bytes(artifact.read_bytes()+b"corrupt")
        try:validate_chunk(result.run_directory,plan.chunks[0],plan,True,"CLEAN_INITIAL_STATE")
        except ArtifactCorruptionError:pass
        else:raise AssertionError("corrupt artifact accepted")
if __name__=="__main__":test_historical_artifact_integrity();print("test_historical_artifact_integrity passed")
