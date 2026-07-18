from dataclasses import replace
from src.research.frameworks.historical.models import HistoricalResearchRunConfig,OverlapMode
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context

def test_historical_warmup_policy():
    configuration=replace(_configuration("opening_range_breakout"),run_id=None);sources=source_bundle(_context("opening_range_breakout",220).frames)
    dependency=plan_historical_run(HistoricalResearchRunConfig("warm_dependency",configuration,"15m",chunk_size_rows=50,warmup_rows=3),sources)
    fixed=plan_historical_run(HistoricalResearchRunConfig("warm_fixed",configuration,"15m",chunk_size_rows=50,warmup_rows=7,overlap_policy=OverlapMode.FIXED_ROWS),sources)
    assert dependency.warmup_rows>=100 and fixed.warmup_rows==7
    assert all(chunk.warmup_prefix_size==chunk.logical_start-chunk.read_start for chunk in dependency.chunks)
if __name__=="__main__":test_historical_warmup_policy();print("test_historical_warmup_policy passed")
