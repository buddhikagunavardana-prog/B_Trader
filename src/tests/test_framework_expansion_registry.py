from pathlib import Path
from src.research.frameworks.configuration import load_research_configuration
from src.tests.framework_expansion_test_data import NEW_NAMES
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.validator import validate_registry
def test_exact_twenty_registry_and_configs():
 assert len(trading_framework_registry.list_names())==20 and NEW_NAMES.issubset(trading_framework_registry.list_names()); assert validate_registry().valid
 configs=list(Path("src/config/framework_research").glob("*.json")); assert len(configs)==20
 for path in configs: load_research_configuration(path)
 try:load_trading_framework("dual_moving_average_crossover",{"fast_period":60,"slow_period":50})
 except ValueError:pass
 else:raise AssertionError("invalid periods accepted")
if __name__=="__main__":test_exact_twenty_registry_and_configs();print("test_framework_expansion_registry passed")
