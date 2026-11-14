"""The same data, fitted by gradient descent with its feature as it comes and standardized.

A flat's price (in thousands) from its area in square metres, with a bias. The loss is a bowl with
two curvatures, one per main direction. Their ratio, the condition number, says how many steps the
slow direction needs at a rate that is safe for the fast one.
"""

import math
import statistics

areas = [52.0, 61.0, 68.0, 75.0, 83.0, 90.0, 98.0, 110.0]
prices = [150.0, 171.0, 185.0, 205.0, 220.0, 238.0, 255.0, 290.0]


def mse(xs: list[float], b: float, w: float) -> float:
    return statistics.fmean((b + w * x - y) ** 2 for x, y in zip(xs, prices))


def descend(xs: list[float], rate: float, steps: int) -> tuple[float, float]:
    b = w = 0.0
    n = len(xs)
    for _ in range(steps):
        misses = [b + w * x - y for x, y in zip(xs, prices)]
        grad_b = 2 / n * sum(misses)
        grad_w = 2 / n * sum(miss * x for miss, x in zip(misses, xs))
        b, w = b - rate * grad_b, w - rate * grad_w
    return b, w


def curvatures(xs: list[float]) -> tuple[float, float]:
    """The eigenvalues of the loss's matrix of second derivatives, 2 * [[1, m1], [m1, m2]]."""
    m1, m2 = statistics.fmean(xs), statistics.fmean(x * x for x in xs)
    half_trace, det = (1 + m2) / 2, m2 - m1 * m1
    root = math.sqrt(half_trace**2 - det)
    return 2 * (half_trace + root), 2 * (half_trace - root)


mean, spread = statistics.fmean(areas), statistics.pstdev(areas)
standardized = [(x - mean) / spread for x in areas]
lowest = mse(standardized, *descend(standardized, 0.5, 1))  # the bottom of the bowl, see below

for name, xs in [("as it comes", areas), ("standardized", standardized)]:
    big, small = curvatures(xs)
    rate = 1 / big
    print(f"{name}: curvatures {big:.4g} and {small:.4g}, condition number {big / small:.4g}")
    for steps in [10, 100, 10_000]:
        excess = mse(xs, *descend(xs, rate, steps)) - lowest
        print(f"  rate {rate:.4g}, {steps:>6} steps: loss above the lowest {excess:.4f}")
print(f"lowest loss {lowest:.4f}")
