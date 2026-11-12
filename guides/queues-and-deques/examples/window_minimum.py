"""After every new offer, the cheapest offer of the last 10 minutes, kept up to date with a deque.

Offers arrive in time order as (minute, price). An offer counts while it is less than 10 minutes
old. The deque holds only the offers that could still be the cheapest one, the oldest in front.
"""

from collections import deque

WINDOW = 10
OFFERS = [(0, 42), (1, 38), (3, 40), (4, 45), (8, 39), (11, 41), (12, 44), (15, 43), (19, 47)]


def cheapest_in_window(offers: list[tuple[int, int]], show: bool = False):
    candidates: deque[tuple[int, int]] = deque()  # prices rise from front to back
    answers, pushes, pops = [], 0, 0
    for minute, price in offers:
        while candidates and candidates[-1][1] >= price:
            candidates.pop()  # never the cheapest again: the new offer costs no more, lasts longer
            pops += 1
        candidates.append((minute, price))
        pushes += 1
        while candidates[0][0] <= minute - WINDOW:
            candidates.popleft()  # too old to count
            pops += 1
        answers.append(candidates[0][1])
        if show:
            shown = " ".join(f"{m}:{p}" for m, p in candidates)
            print(f"minute {minute:>2}, price {price}: cheapest {answers[-1]}, deque {shown}")
    return answers, pushes, pops


def cheapest_by_scanning(offers: list[tuple[int, int]]) -> list[int]:
    answers = []
    for index, (minute, _) in enumerate(offers):
        start = index
        while start > 0 and offers[start - 1][0] > minute - WINDOW:
            start -= 1
        answers.append(min(price for _, price in offers[start : index + 1]))
    return answers


cheapest_in_window(OFFERS, show=True)

generated = [(index * 2 // 3, 30 + index * 37 % 41) for index in range(20_000)]
answers, pushes, pops = cheapest_in_window(generated)
agrees = answers == cheapest_by_scanning(generated)
print(f"{len(generated):,} offers: same answers as a scan: {agrees}")
print(f"pushes {pushes:,}, pops {pops:,}: never more than one of each per offer")
