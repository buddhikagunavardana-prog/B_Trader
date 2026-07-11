from src.research.pipeline.pipeline_context import PipelineTask


def build_strategy_pair_tasks(
    records: list,
    pairs: list[str],
    timeframe: str,
    metadata_builder=None,
) -> list[PipelineTask]:
    tasks = []

    for item_index, record in enumerate(records):
        for pair_index, pair in enumerate(pairs):
            metadata = metadata_builder(record, pair) if metadata_builder else {}
            tasks.append(PipelineTask(
                item_index=item_index,
                pair_index=pair_index,
                pair=pair,
                payload=record,
                timeframe=timeframe,
                metadata=metadata,
            ))

    return tasks
