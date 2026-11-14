"""Least squares and ridge regression on two features that almost always agree.

Two inspectors measure the size of the same flats, each with small errors, and the label depends
on the true size. With ten training examples, least squares can trade a huge weight on one
measurement against a huge negative weight on the other. Ridge regression adds a penalty on the
squared weights to the mean squared error, which in the equations below, written with sums,
adds n times the strength to the diagonal, n being the number of training examples.
"""

import random

rng = random.Random(6)


def example() -> tuple[float, float, float]:
    size = 1 + 5 * rng.random()
    first = size + 0.1 * (rng.random() - 0.5)
    second = size + 0.1 * (rng.random() - 0.5)
    return first, second, 2 * size + 2 * (rng.random() - 0.5)


train = [example() for _ in range(10)]
test = [example() for _ in range(1000)]

# Centre on the training means, so that the bias is the mean label and is not penalized.
means = [sum(row[j] for row in train) / len(train) for j in range(3)]


def centred(rows):
    return [tuple(value - mean for value, mean in zip(row, means)) for row in rows]


def fit(strength: float) -> tuple[float, float]:
    rows = centred(train)
    n = len(train)
    a = sum(x1 * x1 for x1, _, _ in rows) + n * strength
    b = sum(x1 * x2 for x1, x2, _ in rows)
    c = sum(x2 * x2 for _, x2, _ in rows) + n * strength
    p = sum(x1 * y for x1, _, y in rows)
    q = sum(x2 * y for _, x2, y in rows)
    det = a * c - b * b  # solve [[a, b], [b, c]] @ [w1, w2] = [p, q]
    return (c * p - b * q) / det, (a * q - b * p) / det


def mse(rows, w1: float, w2: float) -> float:
    return sum((w1 * x1 + w2 * x2 - y) ** 2 for x1, x2, y in centred(rows)) / len(rows)


print("strength      w1      w2   training MSE   test MSE")
for strength in [0, 0.01, 0.1, 1]:
    w1, w2 = fit(strength)
    errors = f"{mse(train, w1, w2):12.3f}   {mse(test, w1, w2):8.3f}"
    print(f"{strength:8} {w1:7.2f} {w2:7.2f}   {errors}")
