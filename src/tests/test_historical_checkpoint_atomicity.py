import tempfile
from pathlib import Path
from src.tests.historical_test_data import historical_case
from src.research.frameworks.historical.checkpoints import load_checkpoint,write_checkpoint

def test_historical_checkpoint_atomicity():
    with tempfile.TemporaryDirectory() as root:
        _,result,_,_,_,_=historical_case("ema_ribbon_trend",80,40,root)
        path=Path(result.run_directory)/"chunks/chunk_000000/checkpoint.json";checkpoint=load_checkpoint(path);write_checkpoint(path,checkpoint)
        assert load_checkpoint(path)==checkpoint and not list(path.parent.glob("*.tmp"))
if __name__=="__main__":test_historical_checkpoint_atomicity();print("test_historical_checkpoint_atomicity passed")
