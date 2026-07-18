from pathlib import Path

from src.research.frameworks.historical.exceptions import CheckpointCorruptionError, UnsupportedSchemaVersionError
from src.research.frameworks.historical.models import ChunkCheckpoint
from src.research.frameworks.historical.storage import atomic_json, read_json

CHECKPOINT_VERSION="1.0"

def checkpoint_path(run_directory,chunk_index):return Path(run_directory)/"chunks"/f"chunk_{chunk_index:06d}"/"checkpoint.json"

def write_checkpoint(path,checkpoint):
    payload=checkpoint.to_dict()
    if payload["checkpoint_version"]!=CHECKPOINT_VERSION:raise UnsupportedSchemaVersionError(f"unsupported checkpoint version: {payload['checkpoint_version']}")
    return atomic_json(path,payload)

def load_checkpoint(path):
    try:payload=read_json(path)
    except Exception as error:raise CheckpointCorruptionError(f"checkpoint unreadable: {path}; rerun chunk") from error
    if payload.get("checkpoint_version")!=CHECKPOINT_VERSION:raise UnsupportedSchemaVersionError(f"unsupported checkpoint version: {payload.get('checkpoint_version')}")
    try:return ChunkCheckpoint.from_dict(payload)
    except Exception as error:raise CheckpointCorruptionError(f"checkpoint schema invalid: {path}; rerun chunk") from error
