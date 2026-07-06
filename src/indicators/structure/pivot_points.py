def calculate_pivot_points(df):
    pivot = (df["high"] + df["low"] + df["close"]) / 3

    r1 = (2 * pivot) - df["low"]
    s1 = (2 * pivot) - df["high"]

    r2 = pivot + (df["high"] - df["low"])
    s2 = pivot - (df["high"] - df["low"])

    r3 = df["high"] + 2 * (pivot - df["low"])
    s3 = df["low"] - 2 * (df["high"] - pivot)

    return pivot, r1, r2, r3, s1, s2, s3