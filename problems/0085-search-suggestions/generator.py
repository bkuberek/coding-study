"""Seeded inputs for search-suggestions.

`n` is the number of distinct products. Half of the inputs use the letters `abcd` with names
of 1 to 8 letters, so prefixes are shared by many products; the other half use all 26 letters
with names of 1 to 12 letters. `searchWord` is a product (40%), a product followed by 1 to 3
random letters (15%), a prefix of a product with a changed tail (15%), or a random word of 1
to 10 letters (30%).
"""

import random
import string

MAX_PRODUCTS = 10**4
MAX_LENGTH = 20


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_PRODUCTS)
    if rng.random() < 0.5:
        alphabet, longest = "abcd", 8
    else:
        alphabet, longest = string.ascii_lowercase, 12
    products: set[str] = set()
    while len(products) < count:
        products.add(_random_word(rng, alphabet, 1, longest))
    names = sorted(products)
    rng.shuffle(names)
    roll = rng.random()
    product = rng.choice(names)
    if roll < 0.40:
        search_word = product
    elif roll < 0.55:
        search_word = (product + _random_word(rng, alphabet, 1, 3))[:MAX_LENGTH]
    elif roll < 0.70:
        search_word = product[: rng.randint(1, len(product))] + _random_word(rng, alphabet, 1, 3)
    else:
        search_word = _random_word(rng, alphabet, 1, 10)
    return {"products": names, "searchWord": search_word[:MAX_LENGTH]}


def validate(case_input: dict) -> None:
    products, search_word = case_input["products"], case_input["searchWord"]
    assert 1 <= len(products) <= MAX_PRODUCTS, "product count out of range"
    assert len(set(products)) == len(products), "products must be distinct"
    for text in [*products, search_word]:
        assert 1 <= len(text) <= MAX_LENGTH, "length out of range"
        assert all("a" <= letter <= "z" for letter in text), "only lowercase letters"


def _random_word(rng: random.Random, alphabet: str, shortest: int, longest: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(shortest, longest)))
