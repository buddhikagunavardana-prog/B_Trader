import tempfile,time
from pathlib import Path
from src.research.frameworks.historical.locking import ChunkLock
from src.research.frameworks.historical.exceptions import LockAcquisitionError

def test_historical_locking():
    with tempfile.TemporaryDirectory() as root:
        path=Path(root)/"chunk.lock";first=ChunkLock(path).acquire()
        try:
            try:ChunkLock(path).acquire()
            except LockAcquisitionError:pass
            else:raise AssertionError("duplicate lock acquired")
        finally:first.release()
        path.write_text("stale",encoding="utf-8");old=time.time()-1000
        import os;os.utime(path,(old,old))
        second=ChunkLock(path,stale_timeout_seconds=1).acquire();second.release();assert not path.exists()
if __name__=="__main__":test_historical_locking();print("test_historical_locking passed")
