"""Fit a line by least squares, check it against the standard library, and see that it is the
lowest point of the mean squared error.

Each example is a delivery: its distance in kilometres (the feature) and how many minutes it took
(the label).
"""

import statistics

distances = [2, 4, 5, 7, 9, 12, 14, 15]
minutes = [18, 22, 27, 30, 35, 41, 47, 49]


def mse(slope: float, intercept: float) -> float:
    return statistics.fmean((slope * x + intercept - y) ** 2 for x, y in zip(distances, minutes))


# Least squares for one feature: the slope is how x and y vary together, over how x varies.
x_mean, y_mean = statistics.fmean(distances), statistics.fmean(minutes)
together = sum((x - x_mean) * (y - y_mean) for x, y in zip(distances, minutes))
alone = sum((x - x_mean) ** 2 for x in distances)
slope = together / alone
intercept = y_mean - slope * x_mean
print(f"by hand:          slope {slope:.4f}, intercept {intercept:.4f}")

library = statistics.linear_regression(distances, minutes)
print(f"by the library:   slope {library.slope:.4f}, intercept {library.intercept:.4f}")
print(f"10 km predicted:  {slope * 10 + intercept:.1f} minutes")

print(f"MSE of the fit:    {mse(slope, intercept):.3f}")
for name, (s, i) in {
    "slope + 0.2": (slope + 0.2, intercept),
    "slope - 0.2": (slope - 0.2, intercept),
    "intercept + 1": (slope, intercept + 1),
    "intercept - 1": (slope, intercept - 1),
}.items():
    label = f"{name}:"
    print(f"MSE, {label:<15}{mse(s, i):.3f}")
