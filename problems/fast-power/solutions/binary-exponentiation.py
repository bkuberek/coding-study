def my_pow(x: float, n: int) -> float:
    if n < 0:
        x, n = 1 / x, -n
    result = 1.0
    # Invariant: result * x^n equals the original x^n.
    while n > 0:
        if n & 1:
            result *= x
        x *= x
        n >>= 1
    return result
