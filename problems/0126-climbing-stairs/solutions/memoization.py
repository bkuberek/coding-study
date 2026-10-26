from functools import cache


def climb_stairs(n: int) -> int:
    @cache
    def ways(step: int) -> int:
        # One way to stand on the ground (step 0), one way to reach step 1.
        if step <= 1:
            return 1
        return ways(step - 1) + ways(step - 2)

    return ways(n)
