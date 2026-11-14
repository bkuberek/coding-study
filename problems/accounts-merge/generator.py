"""Seeded inputs for accounts-merge: one prolific person plus many ordinary ones.

There are n accounts (capped at 1000). A random share of at least a third of them belongs
to one person: each of those accounts lists a common address plus a few addresses of its
own. The remaining accounts belong to people with 1 to 3 accounts each, drawing 1 to 4
addresses (sometimes repeated) from a personal pool of 1 to 5, so their accounts may or may
not end up linked. Names come from a short list, so unrelated people often share a name.
Accounts are shuffled, and addresses are shuffled inside each account.

The common address is what slows naive union-find down: each account that lists it hangs
the root of the earlier accounts under itself, so the chain grows by one per account and
every later find walks all of it, on the order of A^2 steps in total.
"""

import random
import string

MIN_ACCOUNTS = 1
MAX_ACCOUNTS = 1000
MAX_ADDRESSES = 9
NAMES = ["Ada", "Bo", "Cy", "Dee", "Eli", "Fay", "Gus", "Hal", "Ivy", "Jo"]
DOMAINS = ["mail.com", "post.org", "inbox.net", "web.io"]
ALPHABET = string.ascii_lowercase + string.digits


class _Addresses:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.used: set[str] = set()

    def fresh(self) -> str:
        while True:
            local = "".join(self.rng.choice(ALPHABET) for _ in range(self.rng.randint(1, 8)))
            address = f"{local}@{self.rng.choice(DOMAINS)}"
            if address not in self.used:
                self.used.add(address)
                return address


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_ACCOUNTS), MAX_ACCOUNTS)
    addresses = _Addresses(rng)
    accounts: list[list[str]] = []
    prolific = rng.randint((count + 2) // 3, count)
    name = rng.choice(NAMES)
    common = addresses.fresh()
    for _ in range(prolific):
        own = [addresses.fresh() for _ in range(rng.randint(0, 3))]
        listed = [common, *own]
        rng.shuffle(listed)
        accounts.append([name, *listed])
    while len(accounts) < count:
        name = rng.choice(NAMES)
        pool = [addresses.fresh() for _ in range(rng.randint(1, 5))]
        for _ in range(min(rng.randint(1, 3), count - len(accounts))):
            listed = [rng.choice(pool) for _ in range(rng.randint(1, 4))]
            accounts.append([name, *listed])
    rng.shuffle(accounts)
    return {"accounts": accounts}


def validate(case_input: dict) -> None:
    accounts = case_input["accounts"]
    assert MIN_ACCOUNTS <= len(accounts) <= MAX_ACCOUNTS, "account count out of range"
    owner: dict[str, str] = {}
    allowed = set(string.ascii_lowercase + string.digits + "@.")
    for account in accounts:
        assert 2 <= len(account) <= MAX_ADDRESSES + 1, "account length out of range"
        name, listed = account[0], account[1:]
        assert 1 <= len(name) <= 10 and name.isascii() and name.isalpha(), "bad name"
        for address in listed:
            assert 3 <= len(address) <= 30 and set(address) <= allowed, "bad address"
            assert owner.setdefault(address, name) == name, "a shared address needs one name"
