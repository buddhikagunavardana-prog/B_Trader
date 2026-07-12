import pandas as pd

from src.strategies.professional.cross_sectional_relative_strength import rank_relative_strength


def build_relative_strength_overlay(
    market_data: dict[str, pd.DataFrame],
    config: dict | None = None,
    as_of: int | None = None,
) -> pd.DataFrame:
    settings = dict(config or {})
    return rank_relative_strength(market_data, as_of=as_of, **settings)
