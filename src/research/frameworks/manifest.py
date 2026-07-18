from __future__ import annotations
from datetime import datetime, timezone
import json, subprocess
from pathlib import Path
from src.research.run_management.run_identity import stable_identity_hash

ADAPTER_VERSION="1.0.0"

def build_reproducibility_manifest(configuration, framework, prepared, warnings=()):
    deterministic={
        "run_id":configuration.run_id,"configuration_version":configuration.configuration_version,
        "framework":framework.metadata.name,"framework_version":framework.metadata.version,
        "parameters":dict(framework.parameters),"indicator_dependencies":list(framework.metadata.required_indicators),
        "timeframe_roles":dict(configuration.timeframe_roles),"symbol":configuration.symbol,
        "start_timestamp":None if configuration.start_timestamp is None else configuration.start_timestamp.isoformat(),
        "end_timestamp":None if configuration.end_timestamp is None else configuration.end_timestamp.isoformat(),
        "preparation_mode":configuration.preparation_mode.value,"allow_experimental":configuration.allow_experimental,
        "inputs":{role:{"rows":item.row_count,"first":None if item.first_valid_timestamp is None else item.first_valid_timestamp.isoformat(),"last":None if item.last_valid_timestamp is None else item.last_valid_timestamp.isoformat()} for role,item in prepared.items()},
        "adapter_version":ADAPTER_VERSION,
    }
    try: commit=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
    except Exception: commit="UNAVAILABLE"
    return {"deterministic":deterministic,"deterministic_hash":stable_identity_hash(deterministic),"runtime":{"code_commit":commit,"executed_at":datetime.now(timezone.utc).isoformat(),"warnings":list(warnings)}}

def write_reproducibility_manifest(manifest,path):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8"); return target
