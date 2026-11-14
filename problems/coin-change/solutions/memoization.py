import math
from functools import cache


def coin_change(coins: list[int], amount: int) -> int:
    @cache
    def fewest(remaining: int) -> float:
        # The fewest coins that pay `remaining` exactly; infinity when it cannot be paid.
        if remaining == 0:
            return 0
        best = math.inf
        for coin in coins:
            if coin <= remaining:
                best = min(best, 1 + fewest(remaining - coin))
        return best

    answer = fewest(amount)
    return -1 if answer == math.inf else int(answer)
