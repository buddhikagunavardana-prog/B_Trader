def prevent_duplicate_ids(
    records: list[dict],
    key: str,
    label: str = "record",
) -> None:
    seen_ids = set()

    for record in records:
        record_id = record[key]

        if record_id in seen_ids:
            raise ValueError(f"Duplicate {label} ID: {record_id}")

        seen_ids.add(record_id)


def limit_by_task_budget(
    items: list,
    max_tasks: int,
    tasks_per_item: int,
) -> list:
    if tasks_per_item <= 0:
        return items

    allowed_items = max(1, int(max_tasks) // int(tasks_per_item))
    return items[:allowed_items]


def filter_tasks_by_predicate(tasks: list, predicate) -> list:
    filtered = [task for task in tasks if predicate(task)]
    return filtered or tasks
