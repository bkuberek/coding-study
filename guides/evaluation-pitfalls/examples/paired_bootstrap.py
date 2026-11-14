"""Is model B really better than model A? A paired bootstrap over the test cases.

Both models answered the same 300 test cases, and each case is right or wrong for each model. The
models tend to fail on the same hard cases. Resampling the cases with replacement, many times,
shows how much the difference in accuracy could move with another test set of the same size.
"""

import random

rng = random.Random(1)
N = 300

a_right, b_right = [], []
for _ in range(N):
    hardness = rng.random()
    a_right.append(hardness < 0.80)
    shared = rng.random() < 0.7  # most of the time B finds a case as hard as A does
    b_right.append((hardness if shared else rng.random()) < 0.83)

a, b = sum(a_right) / N, sum(b_right) / N
only_a = sum(x and not y for x, y in zip(a_right, b_right))
only_b = sum(y and not x for x, y in zip(a_right, b_right))
print(f"accuracy: A {a:.3f}, B {b:.3f}, difference {b - a:+.3f}")
print(f"cases only A got right: {only_a}, only B: {only_b}, the other {N - only_a - only_b} agree")

differences = []
for _ in range(2000):
    picks = [int(rng.random() * N) for _ in range(N)]  # the same cases for both models
    differences.append(sum(b_right[i] - a_right[i] for i in picks) / N)
differences.sort()
low, high = differences[49], differences[-50]  # the 50th from each end of 2,000
print(f"95% bootstrap interval of the difference: {low:+.3f} to {high:+.3f}")
print(f"resamples where A did at least as well: {sum(d <= 0 for d in differences) / 2000:.1%}")
