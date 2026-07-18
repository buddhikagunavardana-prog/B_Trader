import tempfile
from dataclasses import replace
from src.research.frameworks.historical.models import HistoricalResearchRunConfig,RunStatus
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.recovery import resume_historical_research
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context

def test_historical_resume():
    with tempfile.TemporaryDirectory() as root:
        configuration=replace(_configuration("nr4_nr7_volatility_breakout"),run_id=None);sources=source_bundle(_context(configuration.framework,180).frames)
        plan=plan_historical_run(HistoricalResearchRunConfig("resume",configuration,"15m",chunk_size_rows=60,output_directory=root),sources)
        interrupted=run_historical_research(plan,sources,stop_after_chunks=1);assert interrupted.status is RunStatus.CANCELLED and interrupted.completed_chunks==1
        resumed=resume_historical_research(interrupted.run_directory,sources);assert resumed.status is RunStatus.COMPLETED and resumed.completed_chunks==3
if __name__=="__main__":test_historical_resume();print("test_historical_resume passed")
