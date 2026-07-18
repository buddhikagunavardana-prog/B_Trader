import tempfile
from dataclasses import replace
from pathlib import Path
from src.research.frameworks.historical.cancellation import CancellationToken
from src.research.frameworks.historical.models import HistoricalResearchRunConfig,RunStatus
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context

def test_historical_cancellation():
    with tempfile.TemporaryDirectory() as root:
        configuration=replace(_configuration("ema_ribbon_trend"),run_id=None);sources=source_bundle(_context(configuration.framework,100).frames);plan=plan_historical_run(HistoricalResearchRunConfig("cancel",configuration,"15m",chunk_size_rows=50,output_directory=root),sources)
        token=CancellationToken(Path(root)/"cancel.token");token.cancel();result=run_historical_research(plan,sources,token)
        assert result.status is RunStatus.CANCELLED and result.completed_chunks==0 and not list(Path(result.run_directory).rglob("decisions*"))
if __name__=="__main__":test_historical_cancellation();print("test_historical_cancellation passed")
