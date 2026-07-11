from src.research.optimizer.search.grid_search import GridSearch
from src.research.optimizer.search.random_search import RandomSearch


SEARCH_REGISTRY = {
    "grid": GridSearch,
    "random": RandomSearch,
}


def get_search_algorithm(name: str, *args, **kwargs):
    if name not in SEARCH_REGISTRY:
        raise ValueError(f"Unknown optimizer search algorithm: {name}")

    return SEARCH_REGISTRY[name](*args, **kwargs)
