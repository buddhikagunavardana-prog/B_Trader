from pathlib import Path
from src.research.frameworks.historical.exceptions import HistoricalCancellationError

class CancellationToken:
    def __init__(self,path=None):self.path=None if path is None else Path(path);self._cancelled=False
    def cancel(self):
        self._cancelled=True
        if self.path:self.path.parent.mkdir(parents=True,exist_ok=True);self.path.write_text("cancelled\n",encoding="utf-8")
    @property
    def cancelled(self):return self._cancelled or bool(self.path and self.path.exists())
    def raise_if_cancelled(self):
        if self.cancelled:raise HistoricalCancellationError("historical research cancelled at a safe chunk boundary")
