"""BFS over states nobody listed: measure exactly 4 litres with a 3-litre jug and a 5-litre jug.

A node is a state (litres in the small jug, litres in the big jug), and its neighbors are the states
one pour away, computed when the search reaches it."""

from collections import deque

SMALL, BIG, GOAL = 3, 5, 4


def moves(state: tuple[int, int]):
    small, big = state
    pour_into_big = min(small, BIG - big)
    pour_into_small = min(big, SMALL - small)
    yield "fill small", (SMALL, big)
    yield "fill big", (small, BIG)
    yield "empty small", (0, big)
    yield "empty big", (small, 0)
    yield "small into big", (small - pour_into_big, big + pour_into_big)
    yield "big into small", (small + pour_into_small, big - pour_into_small)


start = (0, 0)
came_from: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = {start: None}
queue = deque([start])
found = None
while queue and found is None:
    state = queue.popleft()
    for move, after in moves(state):
        if after not in came_from:
            came_from[after] = (state, move)
            if GOAL in after:
                found = after
                break
            queue.append(after)

steps = []
state = found
while came_from[state] is not None:
    previous, move = came_from[state]
    steps.append(f"{move:<15} -> {state}")
    state = previous
every_state = (SMALL + 1) * (BIG + 1)
print(f"{len(steps)} pours, after discovering {len(came_from)} of the {every_state} states:")
for step in reversed(steps):
    print(" ", step)
