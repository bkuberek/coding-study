"""Every interleaving of two deposits, tried one by one instead of hoping a thread switch hits.

Each deposit is a generator, and each `yield` marks a point where the other task may run. A tiny
scheduler runs the tasks in a chosen order, so every possible order can be tried and replayed.
"""

from itertools import combinations


def deposit_split(account: dict, amount: int):
    balance = account["balance"]  # read
    yield
    account["balance"] = balance + amount  # write, from what was read
    yield


def deposit_atomic(account: dict, amount: int):
    account["balance"] += amount  # read and write in one step: nothing runs in between
    yield


def run(order: str, deposit) -> int:
    account = {"balance": 0}
    tasks = {"A": deposit(account, 10), "B": deposit(account, 20)}
    for name in order:
        next(tasks[name])
    return account["balance"]


def schedules(steps_each: int) -> list[str]:
    """Every order of the steps of A and B that keeps each task's own steps in order."""
    total = 2 * steps_each
    return ["".join("A" if i in spots else "B" for i in range(total))
            for spots in combinations(range(total), steps_each)]


for deposit, steps in ((deposit_split, 2), (deposit_atomic, 1)):
    results = {order: run(order, deposit) for order in schedules(steps)}
    lost = [order for order, balance in results.items() if balance != 30]
    print(f"{deposit.__name__}: {len(results)} schedules, {len(lost)} lose a deposit")
    for order, balance in results.items():
        print(f"  {order}  balance {balance}")
