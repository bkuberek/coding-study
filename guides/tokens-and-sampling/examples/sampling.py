"""From a model's scores for the next token to one chosen token: softmax, temperature, top-k, top-p."""

import math

# A fake model's scores (logits) for the token after "The cat sat on the".
LOGITS = {"mat": 4.0, "sofa": 3.2, "floor": 3.0, "roof": 1.5, "moon": -1.0}


def softmax(logits: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    scaled = {token: score / temperature for token, score in logits.items()}
    highest = max(scaled.values())
    weights = {token: math.exp(score - highest) for token, score in scaled.items()}
    total = sum(weights.values())
    return {token: weight / total for token, weight in weights.items()}


def best_first(probs: dict[str, float]) -> list[str]:
    return sorted(probs, key=lambda token: -probs[token])


def renormalized(probs: dict[str, float], kept: list[str]) -> dict[str, float]:
    total = sum(probs[token] for token in kept)
    return {token: probs[token] / total for token in kept}


def top_k(probs: dict[str, float], k: int) -> dict[str, float]:
    return renormalized(probs, best_first(probs)[:k])


def top_p(probs: dict[str, float], p: float) -> dict[str, float]:
    """The fewest most likely tokens whose probabilities add up to at least p."""
    kept, mass = [], 0.0
    for token in best_first(probs):
        kept.append(token)
        mass += probs[token]
        if mass >= p:
            break
    return renormalized(probs, kept)


def draw(probs: dict[str, float], u: float) -> str:
    """Pick a token with a number u in [0, 1), which stands in for a random draw."""
    cumulative = 0.0
    for token in best_first(probs):
        cumulative += probs[token]
        if u < cumulative:
            return token
    return best_first(probs)[-1]


def show(probs: dict[str, float]) -> str:
    return "  ".join(f"{token} {probs[token]:.3f}" for token in best_first(probs))


for temperature in (0.5, 1.0, 2.0):
    print(f"temperature {temperature}: {show(softmax(LOGITS, temperature))}")

probs = softmax(LOGITS)
print("greedy:", best_first(probs)[0])
print("top-k, k=2:", show(top_k(probs, 2)))
print("top-p, p=0.9:", show(top_p(probs, 0.9)))
draws = [0.10, 0.55, 0.80, 0.97, 0.999]
print("draws from the full distribution:", [draw(probs, u) for u in draws])
print("draws after top-p 0.9:          ", [draw(top_p(probs, 0.9), u) for u in draws])
