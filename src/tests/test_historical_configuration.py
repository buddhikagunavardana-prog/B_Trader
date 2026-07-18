from pathlib import Path
from src.research.frameworks.historical.configuration import load_historical_configuration

def test_historical_configuration():
    files=sorted(Path("src/config/framework_research/historical").glob("*.json"));configs=[load_historical_configuration(path) for path in files]
    assert len(configs)==6 and len({config.run_name for config in configs})==6
    assert all(config.resume_enabled and config.strict_integrity_mode for config in configs)
if __name__=="__main__":test_historical_configuration();print("test_historical_configuration passed")
