"""A recursive function, the calls waiting on the stack, and the limit on how deep they go."""

import sys


def traced_digit_sum(n: int, depth: int = 0) -> int:
    """The sum of the decimal digits of n >= 0, printing every call and every return."""
    indent = "  " * depth
    print(f"{indent}call digit_sum({n})")
    result = n  # base case: one digit is its own sum
    if n >= 10:  # smaller case: the last digit, plus the digit sum of the number without it
        result = n % 10 + traced_digit_sum(n // 10, depth + 1)
    print(f"{indent}return {result} from digit_sum({n})")
    return result


traced_digit_sum(4096)


def hanoi(discs: int, source: str, spare: str, target: str, moves: list[str]) -> None:
    """Move a tower of discs from source to target, never putting a disc on a smaller one."""
    if discs == 0:  # base case: an empty tower needs no moves
        return
    hanoi(discs - 1, source, target, spare, moves)  # clear the way: the smaller tower to spare
    moves.append(f"disc {discs}: {source} -> {target}")  # the largest disc goes straight across
    hanoi(discs - 1, spare, source, target, moves)  # the smaller tower back on top of it


moves: list[str] = []
hanoi(3, "A", "B", "C", moves)
print("3 discs:", "; ".join(moves))
counts = []
for discs in range(1, 11):
    moves = []
    hanoi(discs, "A", "B", "C", moves)
    counts.append(len(moves))
print("moves for 1 to 10 discs:", counts)
print("2^n - 1 for 1 to 10:     ", [2**discs - 1 for discs in range(1, 11)])


def digit_sum(n: int) -> int:
    return n if n < 10 else n % 10 + digit_sum(n // 10)


def digit_sum_loop(n: int) -> int:
    total = 0
    while n >= 10:
        total, n = total + n % 10, n // 10
    return total + n


print("recursion limit:", sys.getrecursionlimit())
nines = 10**5000 - 1  # 5000 digits, so the recursion would be 5000 calls deep
try:
    print(digit_sum(nines))
except RecursionError:
    print("digit_sum of 5000 nines: RecursionError")
print("digit_sum_loop of 5000 nines:", digit_sum_loop(nines))
