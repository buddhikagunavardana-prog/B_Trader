from pathlib import Path
from tempfile import TemporaryDirectory
from src.research.frameworks.configuration import load_research_configuration, save_research_configuration


def test_all_35_configurations_round_trip():
    paths = sorted(Path("src/config/framework_research").glob("*.json")); assert len(paths) == 35
    with TemporaryDirectory() as directory:
        for path in paths:
            config = load_research_configuration(path); target = Path(directory) / path.name
            save_research_configuration(config, target)
            assert load_research_configuration(target).to_dict() == config.to_dict()


if __name__ == "__main__":
    test_all_35_configurations_round_trip(); print("test_framework_expansion_35_configuration passed")
