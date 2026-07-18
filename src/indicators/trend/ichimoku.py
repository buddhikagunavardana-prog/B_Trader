import pandas as pd

from src.indicators._validation import positive_int, require_columns


def calculate_ichimoku_cloud(
    df: pd.DataFrame,
    conversion_period: int = 9,
    base_period: int = 26,
    span_b_period: int = 52,
    displacement: int = 26,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calculate causal Ichimoku components aligned to their availability."""
    conversion_period = positive_int(conversion_period, "conversion_period")
    base_period = positive_int(base_period, "base_period")
    span_b_period = positive_int(span_b_period, "span_b_period")
    displacement = positive_int(displacement, "displacement")
    require_columns(df, ["high", "low", "close"])
    midpoint = lambda period: (
        df["high"].rolling(period).max() + df["low"].rolling(period).min()
    ) / 2.0
    conversion = midpoint(conversion_period).rename("ICHIMOKU_CONVERSION")
    base = midpoint(base_period).rename("ICHIMOKU_BASE")
    span_a = ((conversion + base) / 2.0).shift(displacement).rename("ICHIMOKU_SPAN_A")
    span_b = midpoint(span_b_period).shift(displacement).rename("ICHIMOKU_SPAN_B")
    # Align the lagging span to the row where its value is available. A
    # negative shift would place future closes on earlier rows and leak data.
    lagging = df["close"].shift(displacement).rename("ICHIMOKU_LAGGING")
    return conversion, base, span_a, span_b, lagging
