import tempfile
from pathlib import Path
from src.tests.historical_test_data import historical_case
from src.research.frameworks.historical.recovery import recover_historical_run

def test_historical_recovery():
    with tempfile.TemporaryDirectory() as root:
        plan,result,_,_,_,_=historical_case("ema_ribbon_trend",150,50,root)
        chunk=Path(result.run_directory)/"chunks/chunk_000001";artifact=next(chunk.glob("decisions*"));artifact.unlink()
        report=recover_historical_run(result.run_directory,plan)
        assert len(report.retained_chunks)==1 and len(report.chunks_to_rerun)==2
        assert (Path(result.run_directory)/"superseded/chunk_000001/checkpoint.json").exists()
if __name__=="__main__":test_historical_recovery();print("test_historical_recovery passed")
