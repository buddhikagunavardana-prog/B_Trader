import pandas as pd


def calculate_obv(df):
    if df.empty:
        return pd.Series(dtype=float, index=df.index, name="OBV")
    obv = [0]

    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.append(obv[-1] + df["volume"].iloc[i])
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.append(obv[-1] - df["volume"].iloc[i])
        else:
            obv.append(obv[-1])

    return df["volume"].copy().__class__(obv, index=df.index)
