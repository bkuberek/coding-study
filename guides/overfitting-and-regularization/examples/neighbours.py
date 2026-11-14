"""Training error and test error as a model gets more flexible.

The model is k-nearest-neighbour regression: it predicts the average label of the k training
examples whose feature is closest. With k = 1 it repeats the nearest label, noise and all; with k
equal to the whole training set it predicts the same average everywhere.
"""

import random

rng = random.Random(5)


def truth(x: float) -> float:
    return 0.03 * (x - 2) * (x - 5) * (x - 8)


def noisy(x: float) -> float:
    return truth(x) + 3 * (rng.random() - 0.5)  # noise spread evenly between -1.5 and 1.5


train = [(x, noisy(x)) for x in (10 * rng.random() for _ in range(30))]
test = [(x, noisy(x)) for x in (10 * rng.random() for _ in range(200))]


def predict(x: float, k: int) -> float:
    nearest = sorted(range(len(train)), key=lambda i: (abs(train[i][0] - x), i))[:k]
    return sum(train[i][1] for i in nearest) / k


def mse(rows: list[tuple[float, float]], k: int) -> float:
    return sum((predict(x, k) - y) ** 2 for x, y in rows) / len(rows)


print(" k   training MSE   test MSE")
for k in [1, 3, 7, 15, 30]:
    print(f"{k:2}   {mse(train, k):12.3f}   {mse(test, k):8.3f}")
print(f"noise alone: an MSE of {3**2 / 12:.3f} that no model can remove")
