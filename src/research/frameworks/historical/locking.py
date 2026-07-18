from __future__ import annotations

import json, os, socket, time
from pathlib import Path

from src.research.frameworks.historical.exceptions import LockAcquisitionError


class ChunkLock:
    def __init__(self,path,stale_timeout_seconds=300):self.path=Path(path);self.stale=stale_timeout_seconds;self.acquired=False
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists() and time.time()-self.path.stat().st_mtime>self.stale:self.path.unlink(missing_ok=True)
        try:descriptor=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError as error:raise LockAcquisitionError(f"chunk lock already held: {self.path}; retry after stale timeout") from error
        with os.fdopen(descriptor,"w",encoding="utf-8") as handle:json.dump({"pid":os.getpid(),"host":socket.gethostname(),"acquired_epoch":time.time()},handle)
        self.acquired=True;return self
    def release(self):
        if self.acquired:self.path.unlink(missing_ok=True);self.acquired=False
    def __enter__(self):return self.acquire()
    def __exit__(self,*_):self.release()
