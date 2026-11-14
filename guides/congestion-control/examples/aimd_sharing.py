"""Why windows grow by adding and shrink by halving: two flows sharing one link.

Each round, both flows grow their windows; when together they send more than the link carries,
both see a loss and shrink. With additive increase and multiplicative decrease (AIMD), the gap
between them stays the same while they grow and halves at every loss, so they end up close to
equal shares. With additive decrease instead, the gap never closes.
"""

CAPACITY = 60  # segments per round that the link carries


def share(start: tuple[int, int], decrease: str, rounds: int = 120) -> list[tuple[int, int]]:
    a, b = start
    after_losses = []
    for _ in range(rounds):
        a, b = a + 1, b + 1  # additive increase: one segment per round each
        if a + b > CAPACITY:
            if decrease == "halve":
                a, b = max(a // 2, 1), max(b // 2, 1)
            else:  # subtract a constant
                a, b = max(a - 10, 1), max(b - 10, 1)
            after_losses.append((a, b))
    return after_losses


for decrease in ("halve", "subtract 10"):
    losses = share((40, 16), decrease)
    shown = ", ".join(f"{a}/{b}" for a, b in losses[:6])
    a, b = losses[-1]
    print(f"{decrease:<11}  windows after each loss: {shown}, ... last {a}/{b}, gap {a - b}")
