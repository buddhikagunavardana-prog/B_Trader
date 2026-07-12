import pandas as pd


def hold_signals(df: pd.DataFrame) -> pd.Series:
    return pd.Series("HOLD", index=df.index, name="SIGNAL")


def buy_signals(df: pd.DataFrame, condition: pd.Series) -> pd.Series:
    signals = hold_signals(df)
    signals.loc[condition.fillna(False)] = "BUY"
    return signals


def indicator_config(strategy, name: str) -> dict:
    return dict(strategy.indicators.get(name, {}))
