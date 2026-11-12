"""Fewest operations that bring n down to 1, where one operation subtracts 1, halves an even number
or divides a multiple of 3 by 3: plain recursion, then the same recursion with a memo."""

from collections import Counter
from functools import cache


def moves(n: int) -> list[int]:
    """The numbers one operation can reach from n."""
    reachable = [n - 1]
    if n % 2 == 0:
        reachable.append(n // 2)
    if n % 3 == 0:
        reachable.append(n // 3)
    return reachable


def plain(n: int, asked: Counter[int]) -> int:
    asked[n] += 1
    if n == 1:
        return 0
    return 1 + min(plain(m, asked) for m in moves(n))


def with_memo(n: int, memo: dict[int, int], asked: Counter[int]) -> int:
    asked[n] += 1
    if n == 1:
        return 0
    if n not in memo:  # first time this question is asked: answer it once and store it
        memo[n] = 1 + min(with_memo(m, memo, asked) for m in moves(n))
    return memo[n]


asked: Counter[int] = Counter()
plain(10, asked)
print("plain recursion from 10 asks:", ", ".join(f"f({n}) {asked[n]}x" for n in sorted(asked)))

for n in (10, 20, 40, 80, 160):
    plain_asked, memo_asked = Counter[int](), Counter[int]()
    answer = plain(n, plain_asked)
    assert with_memo(n, {}, memo_asked) == answer
    print(f"n = {n:3}: {answer} steps", end=" | ")
    print(f"plain: {plain_asked.total():6} calls | memo: {memo_asked.total():3} calls")


@cache
def fewest(n: int) -> int:
    return 0 if n == 1 else 1 + min(fewest(m) for m in moves(n))


print("fewest(10) =", fewest(10), "|", fewest.cache_info())

path = [10]
while path[-1] > 1:  # read the steps back: always move to a number whose answer is one less
    path.append(next(m for m in moves(path[-1]) if fewest(m) == fewest(path[-1]) - 1))
print("best path from 10:", " -> ".join(map(str, path)))
greedy = [10]
while greedy[-1] > 1:  # divide whenever you can: the biggest drop first
    greedy.append(min(moves(greedy[-1])))
print("dividing whenever possible:", " -> ".join(map(str, greedy)))

# A new rule: at most `threes` divisions by 3. The answer now depends on n AND on threes left.
memo_by_n: dict[int, int] = {}


def wrong_key(n: int, threes: int) -> int:
    if n == 1:
        return 0
    if n not in memo_by_n:  # bug: the key forgets how many divisions by 3 are left
        options = [wrong_key(n - 1, threes)]
        if n % 2 == 0:
            options.append(wrong_key(n // 2, threes))
        if n % 3 == 0 and threes > 0:
            options.append(wrong_key(n // 3, threes - 1))
        memo_by_n[n] = 1 + min(options)
    return memo_by_n[n]


@cache
def right_key(n: int, threes: int) -> int:
    if n == 1:
        return 0
    options = [right_key(n - 1, threes)]
    if n % 2 == 0:
        options.append(right_key(n // 2, threes))
    if n % 3 == 0 and threes > 0:
        options.append(right_key(n // 3, threes - 1))
    return 1 + min(options)


print("9 with at most one division by 3:", end=" ")
print("key n ->", wrong_key(9, 1), "| key (n, threes) ->", right_key(9, 1))

fewest.cache_clear()
try:
    fewest(5000)
except RecursionError:
    print("fewest(5000) from an empty cache: RecursionError")
table = [0, 0]  # table[k] = fewest steps from k, filled from small k up; table[0] is unused
for k in range(2, 5001):
    table.append(1 + min(table[m] for m in moves(k)))
print("the same answers filled from 2 up to 5000 with a loop: fewest(5000) =", table[5000])
