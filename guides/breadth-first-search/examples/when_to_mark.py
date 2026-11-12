"""Mark a node when it enters the queue, not when it leaves: same distances, very different costs.

The graph is a club of 30 members in which everybody knows everybody, so every node is discovered
again and again."""

from collections import deque

MEMBERS = 30
everyone = range(MEMBERS)
knows = {member: [other for other in everyone if other != member] for member in everyone}


def mark_on_entry(start: int) -> tuple[dict[int, int], int]:
    distance = {start: 0}
    pushes = 1
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for other in knows[node]:
            if other not in distance:
                distance[other] = distance[node] + 1
                queue.append(other)
                pushes += 1
    return distance, pushes


def mark_on_exit(start: int) -> tuple[dict[int, int], int]:
    distance: dict[int, int] = {}
    pushes = 1
    queue = deque([(start, 0)])
    while queue:
        node, steps = queue.popleft()
        if node in distance:  # a copy that waited in the queue while another copy was handled
            continue
        distance[node] = steps
        for other in knows[node]:
            if other not in distance:
                queue.append((other, steps + 1))
                pushes += 1
    return distance, pushes


early, early_pushes = mark_on_entry(0)
late, late_pushes = mark_on_exit(0)
print("same distances:", early == late)
print("pushes when marking on entry:", early_pushes)
print("pushes when marking on exit: ", late_pushes)
