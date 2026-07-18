import json
from tempfile import TemporaryDirectory
from pathlib import Path

from types import SimpleNamespace

from src.research.frameworks.configuration import configuration_from_dict, enforce_experimental_access, load_research_configuration, save_research_configuration
from src.research.frameworks.exceptions import ResearchConfigurationError
from src.tests.framework_research_test_data import research_configuration
from src.trading_frameworks.models import FrameworkStability


def test_configuration_roundtrip_examples_alias_and_stable_identity():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "config.json"; config = research_configuration("turtle_trading")
        save_research_configuration(config, path)
        assert load_research_configuration(path).to_dict() == config.to_dict()
    alias = research_configuration("turtle")
    assert configuration_from_dict(alias.to_dict()).framework == "turtle_trading"
    for path in Path("src/config/framework_research").glob("*.json"):
        assert load_research_configuration(path).configuration_version == "1.0"


def test_invalid_configuration_cases_are_rejected():
    base = research_configuration("turtle_trading").to_dict()
    cases = [
        {**base, "framework": "unknown"}, {**base, "parameters": {"entry_period": "twenty"}},
        {**base, "timeframe_roles": {"wrong": "1d"}}, {**base, "primary_role": "wrong"},
        {**base, "start_timestamp": "2026-02-01Z", "end_timestamp": "2026-01-01Z"},
        {**base, "output_mode": "invalid"}, {**base, "unexpected": True},
    ]
    for data in cases:
        try: configuration_from_dict(data)
        except (ResearchConfigurationError, ValueError): pass
        else: raise AssertionError(f"invalid configuration accepted: {data}")
    experimental = SimpleNamespace(metadata=SimpleNamespace(stability=FrameworkStability.EXPERIMENTAL, required_indicators=()))
    try: enforce_experimental_access(experimental, False)
    except ResearchConfigurationError: pass
    else: raise AssertionError("experimental framework accepted without opt-in")
    enforce_experimental_access(experimental, True)


if __name__ == "__main__":
    test_configuration_roundtrip_examples_alias_and_stable_identity(); test_invalid_configuration_cases_are_rejected(); print("test_framework_research_configuration passed")
