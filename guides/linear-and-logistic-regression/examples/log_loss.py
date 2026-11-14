"""The sigmoid turns any number into a probability, and the log loss charges for a probability
given to the wrong answer far more than the squared error does.
"""

import math


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def log_odds(p: float) -> float:
    return math.log(p / (1 - p))


print("   z   p = sigmoid(z)   log odds of p")
for z in [-4, -2, 0, 2, 4]:
    print(f"{z:4}   {sigmoid(z):14.4f}   {log_odds(sigmoid(z)):13.1f}")

print()
print("p of the right answer   log loss   squared error")
for p in [0.99, 0.9, 0.7, 0.5, 0.3, 0.1, 0.01]:
    print(f"{p:20}   {-math.log(p):8.3f}   {(1 - p) ** 2:13.3f}")
