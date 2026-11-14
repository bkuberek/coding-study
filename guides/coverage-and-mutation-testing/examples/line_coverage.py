"""Line and branch coverage measured with sys.settrace, and what they cannot see.

The tracer records each line of shipping_cost that runs, and each jump from one line to the
next. Three small suites are measured: one test that runs every line, the same call with no
check at all, and a suite that also takes the other side of both decisions.
"""

import sys


def shipping_cost(weight_kg: int, express: bool) -> int:
    cost = 5
    if weight_kg > 2:
        cost += 3 * (weight_kg - 2)
    if express:
        cost *= 2
    return cost


FIRST = shipping_cost.__code__.co_firstlineno
BODY = {line - FIRST for _, _, line in shipping_cost.__code__.co_lines()
        if line is not None and line > FIRST}


def measure(suite) -> tuple[set[int], set[tuple[int, int]]]:
    lines, arcs, previous = set(), set(), [None]

    def tracer(frame, event, arg):
        if frame.f_code is not shipping_cost.__code__:
            return None
        if event == "call":
            previous[0] = None
        elif event == "line":
            line = frame.f_lineno - FIRST
            lines.add(line)
            if previous[0] is not None:
                arcs.add((previous[0], line))
            previous[0] = line
        return tracer

    sys.settrace(tracer)
    try:
        suite()
    finally:
        sys.settrace(None)
    return lines, arcs


def one_test():
    assert shipping_cost(3, True) == 16


def no_check():
    shipping_cost(3, True)  # runs the code, checks nothing


def both_sides():
    assert shipping_cost(3, True) == 16
    assert shipping_cost(1, False) == 5


_, all_arcs = measure(both_sides)
for suite in (one_test, no_check, both_sides):
    lines, arcs = measure(suite)
    missing = ", ".join(f"{a}->{b}" for a, b in sorted(all_arcs - arcs)) or "none"
    print(f"{suite.__name__:<10} lines {len(lines)}/{len(BODY)}, "
          f"jumps {len(arcs)}/{len(all_arcs)}, jumps never taken: {missing}")
