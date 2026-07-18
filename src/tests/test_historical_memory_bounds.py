import tempfile
from dataclasses import replace
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.historical.validation import validate_memory_bound
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context

def test_historical_memory_bounds():
    with tempfile.TemporaryDirectory() as root:
        configuration=replace(_configuration("pin_bar_rejection"),run_id=None);sources=source_bundle(_context(configuration.framework,300).frames)
        safe=plan_historical_run(HistoricalResearchRunConfig("memory_safe",configuration,"15m",chunk_size_rows=60,output_directory=root,maximum_memory_bytes=20_000_000),sources);assert validate_memory_bound(safe,sources)["valid"]
        unsafe=plan_historical_run(HistoricalResearchRunConfig("memory_unsafe",configuration,"15m",chunk_size_rows=300,output_directory=root,maximum_memory_bytes=100),sources)
        try:run_historical_research(unsafe,sources)
        except MemoryError:pass
        else:raise AssertionError("unsafe memory estimate accepted")
if __name__=="__main__":test_historical_memory_bounds();print("test_historical_memory_bounds passed")
