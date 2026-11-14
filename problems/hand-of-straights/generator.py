"""Seeded inputs for hand-of-straights.

`n` is about the number of cards, clamped to 1..10^4. The group size is drawn from 1 to 10
(sometimes up to the whole hand), and the hand is built from straights whose starting values
cluster in a narrow window, so many straights overlap and share values. Two inputs in five are
then broken: one card is moved to a neighboring value (which leaves a gap in some straight) or
one card is removed (which also breaks the card count). Values sit in a random window inside
0..10^9, and the hand is shuffled.

From UNIFORM_FROM cards on (the bench ladder), every hand has one shape instead: groups of
UNIFORM_GROUP cards, every straight starting within UNIFORM_WINDOW values of the lowest, and no
break. Every approach then reads the whole hand (a card count that is not a multiple of the
group size, or an early gap, would let it answer false at once), and each value has about
n / 9 copies, so the brute force scans past a share of the hand to remove each card.
"""

import random

MIN_CARDS = 1
MAX_CARDS = 10**4
MAX_VALUE = 10**9
SMALL_GROUP = 10
BROKEN_SHARE = 0.4
UNIFORM_FROM = 100
UNIFORM_GROUP = 5
UNIFORM_WINDOW = 4


def generate(rng: random.Random, n: int) -> dict:
    cards = min(max(n, MIN_CARDS), MAX_CARDS)
    uniform = cards >= UNIFORM_FROM
    if uniform:
        group_size = UNIFORM_GROUP
    else:
        group_size = rng.randint(1, min(cards, SMALL_GROUP)) if rng.random() < 0.9 else cards
    groups = max(1, cards // group_size)
    window = UNIFORM_WINDOW if uniform else rng.randint(1, max(1, groups // 2))
    base = rng.randint(0, MAX_VALUE - window - group_size)
    hand = []
    for _ in range(groups):
        start = base + rng.randint(0, window)
        hand.extend(range(start, start + group_size))
    if not uniform and rng.random() < BROKEN_SHARE:
        position = rng.randrange(len(hand))
        if len(hand) > 1 and rng.random() < 0.5:
            hand.pop(position)
        else:
            step = 1 if hand[position] < MAX_VALUE else -1
            hand[position] += step
    rng.shuffle(hand)
    return {"hand": hand, "groupSize": min(group_size, len(hand))}


def validate(case_input: dict) -> None:
    hand, group_size = case_input["hand"], case_input["groupSize"]
    assert MIN_CARDS <= len(hand) <= MAX_CARDS, "number of cards out of range"
    assert all(0 <= value <= MAX_VALUE for value in hand), "card value out of range"
    assert 1 <= group_size <= len(hand), "group size out of range"
