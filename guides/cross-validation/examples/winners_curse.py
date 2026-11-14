"""Choosing the best of many models by their validation score, when none of them is any good.

The labels are coin flips and so are the 50 models' answers, so every model's true accuracy is
50%. Each is scored on the same 40 validation examples, and the best one is kept. Its validation
score is then compared with its score on 10,000 fresh examples.
"""

import random
import statistics

rng = random.Random(4)


def coin() -> int:
    return 1 if rng.random() < 0.5 else 0


validation = [coin() for _ in range(40)]
answers = [[coin() for _ in validation] for _ in range(50)]
scores = [sum(a == y for a, y in zip(model, validation)) / len(validation) for model in answers]

low, middle, high = min(scores), statistics.median(scores), max(scores)
print(f"validation accuracy: worst {low:.3f}, median {middle:.3f}, best {high:.3f}")
fresh = sum(coin() == coin() for _ in range(10_000)) / 10_000  # the winner still guesses
print(f"the winner on fresh examples: {fresh:.3f}")
