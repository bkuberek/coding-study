import math


def my_pow(x: float, n: int) -> float:
    base = x if n >= 0 else 1 / x
    remaining = abs(n)
    result = 1.0
    done = 0
    while done < remaining:
        result *= base
        done += 1
        if result == 1.0:
            # base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
            remaining = (remaining - done) % done
            done = 0
        elif result == 0.0 or math.isinf(result):
            break  # further multiplications cannot change the result
    return result
