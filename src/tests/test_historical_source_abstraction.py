import tempfile
from pathlib import Path
from src.research.frameworks.historical.source import InMemoryDataFrameSource,LocalCsvSource
from src.utils.trading_framework_performance import _context

def test_historical_source_abstraction():
    frame=_context("ema_ribbon_trend",50).frames["execution"];memory=InMemoryDataFrameSource(frame);memory.validate()
    with tempfile.TemporaryDirectory() as root:
        path=Path(root)/"source.csv";frame.reset_index(names="timestamp").to_csv(path,index=False);local=LocalCsvSource(path);local.validate()
        bounded=local.read_rows(10,20)
        assert local.row_count()==50 and local.fingerprint()==local.fingerprint()
        assert len(bounded)==10 and list(bounded.columns)==list(frame.columns) and bounded.index.is_monotonic_increasing
        assert not hasattr(local,"_cache") and local.descriptor()["source_type"]=="csv"
        try:local.read_rows(-1,2)
        except IndexError:pass
        else:raise AssertionError("invalid bounded read accepted")
if __name__=="__main__":test_historical_source_abstraction();print("test_historical_source_abstraction passed")
