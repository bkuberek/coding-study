"""Seeded inputs for daily-temperatures: a cold spell followed by noisy weather.

The log starts with a cold spell covering a third to two thirds of the days: readings that
never rise from one day to the next (they repeat or drop), starting high in the range. The
other days are uniform noise over the whole range. No day of the spell finds a warmer day
inside the spell, so scanning ahead from each day reads at least (spell length)^2 / 2, about
n^2 / 18 to 2n^2 / 9 readings. The stack holds the whole spell at its peak and still touches
each day at most twice.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
LOW = -50
HIGH = 50
SPELL_TOP_MIN = 30


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    spell_length = rng.randint(length // 3, (2 * length) // 3)
    top = rng.randint(SPELL_TOP_MIN, HIGH)
    bottom = rng.randint(LOW, top)
    spell = sorted((rng.randint(bottom, top) for _ in range(spell_length)), reverse=True)
    noise = [rng.randint(LOW, HIGH) for _ in range(length - spell_length)]
    return {"temperatures": spell + noise}


def validate(case_input: dict) -> None:
    temperatures = case_input["temperatures"]
    assert MIN_LENGTH <= len(temperatures) <= MAX_LENGTH, "length out of range"
    assert all(LOW <= value <= HIGH for value in temperatures), "temperature out of range"
