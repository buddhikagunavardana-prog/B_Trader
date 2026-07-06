def calculate_fibonacci_levels(high, low):
    diff = high - low

    return {
        "0.0": high,
        "23.6": high - diff * 0.236,
        "38.2": high - diff * 0.382,
        "50.0": high - diff * 0.500,
        "61.8": high - diff * 0.618,
        "78.6": high - diff * 0.786,
        "100.0": low,
    }