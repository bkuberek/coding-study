"""Recursion keeps its unfinished work on the call stack; a loop can keep it on a stack of its own.

Both functions measure how deeply lists are nested. CPython limits how deep its interpreter stack
may grow (sys.getrecursionlimit()), so the recursive one fails on deep input and the loop does not.
"""

import sys


def depth_recursive(value: object) -> int:
    if not isinstance(value, list):
        return 0
    return 1 + max((depth_recursive(item) for item in value), default=0)


def depth_with_a_stack(value: object) -> int:
    deepest = 0
    pending = [(value, 0)]  # (a value still to look at, how many lists surround it)
    while pending:
        current, around = pending.pop()
        if isinstance(current, list):
            deepest = max(deepest, around + 1)
            pending.extend((item, around + 1) for item in current)
    return deepest


shallow = [1, [2, [3, 4]], [5]]
print("shallow:", depth_recursive(shallow), depth_with_a_stack(shallow))

deep: list = []
for _ in range(4_999):
    deep = [deep]
print("recursion limit:", sys.getrecursionlimit())
try:
    depth_recursive(deep)
except RecursionError:
    print("deep, recursive: RecursionError")
print("deep, with a stack:", depth_with_a_stack(deep))
