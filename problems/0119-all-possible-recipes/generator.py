"""Seeded inputs for all-possible-recipes: long recipe chains with rare blockers.

There are n recipes (capped at 1000) in a random hidden order, plus up to n supplies and a
few missing items that nobody provides. Each recipe uses the previous recipe in the hidden
order with probability 0.8, up to two other earlier recipes, and up to three supplies. A
recipe uses a missing item, or a later recipe (which closes a loop through the chain), with
probability about 1 / n each, so most recipes stay preparable while some fail.

The recipes are then listed in random order. A sweep over that list prepares roughly one
more link of each chain per pass, so sweeping until nothing changes costs about R * I,
while the queue-based and memoized approaches stay linear.
"""

import random
import string

MIN_RECIPES = 1
MAX_RECIPES = 1000
MAX_SUPPLIES = 1000
MAX_INGREDIENTS = 10
MISSING_ITEMS = 5


def _unique_names(rng: random.Random, count: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < count:
        name = "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(3, 10)))
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_RECIPES), MAX_RECIPES)
    supply_count = rng.randint(1, min(count, MAX_SUPPLIES))
    names = _unique_names(rng, count + supply_count + MISSING_ITEMS)
    order = names[:count]
    supplies = names[count : count + supply_count]
    missing = names[count + supply_count :]
    rare = min(0.2, 1 / count)
    needs: dict[str, list[str]] = {}
    for position, recipe in enumerate(order):
        items: set[str] = set()
        if position > 0 and rng.random() < 0.8:
            items.add(order[position - 1])
        if position > 0:
            items.update(order[rng.randrange(position)] for _ in range(rng.randint(0, 2)))
        items.update(rng.choice(supplies) for _ in range(rng.randint(0, 3)))
        if rng.random() < rare:
            items.add(rng.choice(missing))
        if position + 1 < count and rng.random() < rare:
            items.add(order[rng.randrange(position + 1, count)])
        if not items:
            items.add(rng.choice(supplies))
        listed = sorted(items)
        rng.shuffle(listed)
        needs[recipe] = listed
    recipes = order.copy()
    rng.shuffle(recipes)
    rng.shuffle(supplies)
    return {"recipes": recipes, "ingredients": [needs[recipe] for recipe in recipes], "supplies": supplies}


def validate(case_input: dict) -> None:
    recipes, ingredients, supplies = case_input["recipes"], case_input["ingredients"], case_input["supplies"]
    assert MIN_RECIPES <= len(recipes) <= MAX_RECIPES, "recipe count out of range"
    assert len(ingredients) == len(recipes), "one ingredient list per recipe"
    assert 1 <= len(supplies) <= MAX_SUPPLIES, "supply count out of range"
    assert all(1 <= len(items) <= MAX_INGREDIENTS for items in ingredients), "ingredient count out of range"
    assert all(len(set(items)) == len(items) for items in ingredients), "repeated ingredient"
    letters = set(string.ascii_lowercase)
    every_name = [*recipes, *supplies, *(item for items in ingredients for item in items)]
    assert all(1 <= len(name) <= 10 and set(name) <= letters for name in every_name), "bad name"
    assert len(set(recipes) | set(supplies)) == len(recipes) + len(supplies), "names must be distinct"
