from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable


_WORKER_MARKET_DATA = {}


def initialize_worker(market_data: dict) -> None:
    global _WORKER_MARKET_DATA
    _WORKER_MARKET_DATA = market_data


def get_worker_market_data(pair: str):
    return _WORKER_MARKET_DATA[pair]


def execute_tasks(
    tasks: list,
    evaluator: Callable,
    max_workers: int,
    market_data: dict | None = None,
    progress_callback: Callable | None = None,
) -> tuple[list, list]:
    rows = []
    failures = []

    if not tasks:
        return rows, failures

    if max_workers <= 1:
        if market_data is not None:
            initialize_worker(market_data)

        for completed, task in enumerate(tasks, start=1):
            try:
                rows.append(evaluator(task))
                if progress_callback:
                    progress_callback(completed, len(tasks), task, None)
            except Exception as error:
                failures.append({"task": task, "error": str(error)})
                if progress_callback:
                    progress_callback(completed, len(tasks), task, error)

        return rows, failures

    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=initialize_worker,
        initargs=(market_data or {},),
    ) as executor:
        future_map = {
            executor.submit(evaluator, task): task
            for task in tasks
        }

        for completed, future in enumerate(as_completed(future_map), start=1):
            task = future_map[future]
            try:
                rows.append(future.result())
                if progress_callback:
                    progress_callback(completed, len(tasks), task, None)
            except Exception as error:
                failures.append({"task": task, "error": str(error)})
                if progress_callback:
                    progress_callback(completed, len(tasks), task, error)

    return rows, failures
