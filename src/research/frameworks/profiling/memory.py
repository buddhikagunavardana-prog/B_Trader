from __future__ import annotations


def dataframe_memory_bytes(frame) -> int:
    return int(frame.memory_usage(index=True, deep=True).sum())


def result_memory(result, sources) -> dict[str, int]:
    input_bytes = sum(dataframe_memory_bytes(frame) for frame in sources.values())
    output_bytes = dataframe_memory_bytes(result.decisions)
    return {
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "estimated_total_bytes": input_bytes + output_bytes,
    }
