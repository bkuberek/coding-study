from collections.abc import Iterator
from decimal import Decimal

CYCLE = Decimal(-1)


def total_exposure(edges: list[list[str]], contractors: list[str], exposures: list[Decimal], root: str) -> Decimal:
    children: dict[str, list[str]] = {}
    for parent, child in edges:
        children.setdefault(parent, []).append(child)
    own = dict(zip(contractors, exposures, strict=True))
    on_path = {root}  # contractors on the current DFS path; meeting one again closes a cycle
    finished: set[str] = set()  # fully explored contractors, already counted
    total = own.get(root, Decimal(0))
    stack: list[tuple[str, Iterator[str]]] = [(root, iter(children.get(root, [])))]
    while stack:
        node, pending = stack[-1]
        child = next(pending, None)
        if child is None:
            stack.pop()
            on_path.discard(node)
            finished.add(node)
        elif child in on_path:
            return CYCLE
        elif child not in finished:
            on_path.add(child)
            total += own.get(child, Decimal(0))
            stack.append((child, iter(children.get(child, []))))
    return total
