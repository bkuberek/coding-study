"""Gradient descent on a one-weight model, with four learning rates.

The model predicts y = w * x, and the loss is the mean squared error. That loss is a parabola in w
whose curvature is the same everywhere, so each step multiplies the distance to the best w by the
same factor, 1 - rate * curvature.
"""

xs = [1.0, 2.0, 3.0, 4.0]
ys = [2.1, 3.9, 6.2, 7.8]
n = len(xs)


def loss(w: float) -> float:
    return sum((w * x - y) ** 2 for x, y in zip(xs, ys)) / n


def gradient(w: float) -> float:
    return 2 / n * sum((w * x - y) * x for x, y in zip(xs, ys))


curvature = 2 / n * sum(x * x for x in xs)  # the second derivative of the loss
best = sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs)
print(f"curvature {curvature:g}, so rates below {2 / curvature:.4f} converge")
print(f"loss at w = 0: {loss(0):.4f}; best w {best:.4f}, lowest loss {loss(best):.4f}")
print()
print(f"rate   factor   {"loss at 1":>11}{"at 5":>11}{"at 20":>11}   {"w at 20":>10}")
for rate in [0.01, 0.05, 0.12, 0.14]:
    w, losses = 0.0, []
    for step in range(1, 21):
        w -= rate * gradient(w)
        if step in (1, 5, 20):
            losses.append(loss(w))
    after = "".join(f"{value:11.4f}" for value in losses)
    print(f"{rate:.2f}   {1 - rate * curvature:+.2f}   {after}   {w:10.4f}")
