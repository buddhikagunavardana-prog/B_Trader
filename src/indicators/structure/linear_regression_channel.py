import numpy as np
import pandas as pd

from src.indicators._validation import positive_float, positive_int, require_source


def calculate_linear_regression_channel(
    df: pd.DataFrame,
    period: int = 20,
    deviations: float = 2.0,
    source: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    period = positive_int(period, "period")
    deviations = positive_float(deviations, "deviations")
    require_source(df, source)
    x = np.arange(period, dtype=float)
    denominator = ((x - x.mean()) ** 2).sum()

    def regression_end(values: np.ndarray) -> float:
        slope = ((x - x.mean()) * (values - values.mean())).sum() / denominator
        return values.mean() + slope * (period - 1 - x.mean())

    middle = df[source].rolling(period).apply(regression_end, raw=True)
    residual_std = df[source].rolling(period).std()
    upper = (middle + deviations * residual_std).rename("LINEAR_REGRESSION_UPPER")
    lower = (middle - deviations * residual_std).rename("LINEAR_REGRESSION_LOWER")
    return upper, middle.rename("LINEAR_REGRESSION_MIDDLE"), lower
