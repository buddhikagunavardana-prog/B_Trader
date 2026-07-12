import numpy as np
import pandas as pd


def rank_relative_strength(
    market_data: dict[str, pd.DataFrame],
    short_horizon: int = 16,
    medium_horizon: int = 96,
    volatility_period: int = 96,
    top_count: int = 2,
    short_weight: float = 0.40,
    medium_weight: float = 0.60,
    as_of: int | None = None,
) -> pd.DataFrame:
    horizons = [short_horizon, medium_horizon, volatility_period]
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in horizons):
        raise ValueError("momentum and volatility horizons must be positive integers")
    if isinstance(top_count, bool) or not isinstance(top_count, int) or top_count <= 0:
        raise ValueError("top_count must be a positive integer")
    if short_weight < 0 or medium_weight < 0 or not np.isclose(short_weight + medium_weight, 1.0):
        raise ValueError("relative-strength weights must be non-negative and sum to 1")
    if as_of is not None:
        if as_of < 0:
            raise ValueError("as_of must be non-negative")
        market_data = {
            pair: frame.iloc[: as_of + 1]
            for pair, frame in market_data.items()
        }
    rows = []
    btc = market_data.get("BTCUSDT")
    if btc is None or len(btc) <= max(medium_horizon, 192):
        return pd.DataFrame(columns=["Pair", "Score", "Weight", "Rank"])
    btc_healthy = btc["close"].iloc[-1] > btc["close"].ewm(span=192, adjust=False).mean().iloc[-1]
    if not btc_healthy:
        return pd.DataFrame(columns=["Pair", "Score", "Weight", "Rank"])
    timestamp_column = "open_time" if "open_time" in btc.columns else None
    reference_time = btc[timestamp_column].iloc[-1] if timestamp_column else btc.index[-1]
    for pair, df in sorted(market_data.items()):
        if len(df) <= max(medium_horizon, volatility_period):
            continue
        pair_time = df[timestamp_column].iloc[-1] if timestamp_column and timestamp_column in df.columns else df.index[-1]
        if pair_time != reference_time:
            continue
        close = df["close"]
        volatility = close.pct_change(fill_method=None).rolling(volatility_period).std().iloc[-1]
        if not np.isfinite(volatility) or volatility <= 0:
            continue
        rows.append({
            "Pair": pair,
            "Short": close.pct_change(short_horizon, fill_method=None).iloc[-1] / volatility,
            "Medium": close.pct_change(medium_horizon, fill_method=None).iloc[-1] / volatility,
            "Volatility": volatility,
            "Eligible": close.iloc[-1] > close.ewm(span=96, adjust=False).mean().iloc[-1],
        })
    report = pd.DataFrame(rows)
    if report.empty:
        return pd.DataFrame(columns=["Pair", "Score", "Weight", "Rank"])
    for column in ["Short", "Medium"]:
        std = report[column].std(ddof=0)
        report[f"{column}Z"] = 0.0 if std == 0 else (report[column] - report[column].mean()) / std
    report["Score"] = medium_weight * report["MediumZ"] + short_weight * report["ShortZ"]
    median = report["Score"].median()
    selected = report[(report["Eligible"]) & (report["Score"] > 0) & (report["Score"] > median)]
    selected = selected.sort_values(["Score", "Pair"], ascending=[False, True]).head(top_count).copy()
    if selected.empty:
        return pd.DataFrame(columns=["Pair", "Score", "Weight", "Rank"])
    inverse = 1.0 / selected["Volatility"]
    selected["Weight"] = inverse / inverse.sum()
    selected["Rank"] = range(1, len(selected) + 1)
    return selected[["Pair", "Score", "Weight", "Rank"]].reset_index(drop=True)
