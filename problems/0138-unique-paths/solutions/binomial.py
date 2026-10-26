MOD = 10**9 + 7


def unique_paths(m: int, n: int) -> int:
    # A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
    moves = m + n - 2
    chosen = min(m, n) - 1
    numerator = denominator = 1
    for step in range(1, chosen + 1):
        numerator = numerator * (moves - chosen + step) % MOD
        denominator = denominator * step % MOD
    # MOD is prime, so denominator^(MOD - 2) is its inverse (Fermat's little theorem).
    return numerator * pow(denominator, MOD - 2, MOD) % MOD
