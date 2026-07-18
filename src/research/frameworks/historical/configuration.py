from __future__ import annotations

import json
from pathlib import Path

from src.research.frameworks.configuration import configuration_from_dict, load_research_configuration
from src.research.frameworks.historical.models import HistoricalResearchRunConfig


def historical_configuration_from_dict(data,base_directory=None):
    values=dict(data)
    reference=values.pop("framework_configuration_path",None)
    snapshot=values.pop("framework_configuration",None)
    if (reference is None)==(snapshot is None):raise ValueError("provide exactly one framework configuration path or snapshot")
    if reference is not None:
        base=Path(base_directory or ".").resolve();permitted=base.parent if base.name=="historical" else base;path=(base/reference).resolve()
        if permitted not in path.parents and path!=permitted:raise ValueError("framework configuration path escapes framework configuration root")
        framework_configuration=load_research_configuration(path)
    else:framework_configuration=configuration_from_dict(snapshot)
    return HistoricalResearchRunConfig(framework_configuration=framework_configuration,**values)


def load_historical_configuration(path):
    source=Path(path);return historical_configuration_from_dict(json.loads(source.read_text(encoding="utf-8")),source.parent)
