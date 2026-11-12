"""Suggest commands for a mistyped name: every command of the same length with at most one letter
changed, found by walking the trie and branching into the other children where a letter may differ.
"""

COMMANDS = ["branch", "build", "bump", "check", "clean", "clone", "commit", "log", "login", "logout"]


class Node:
    def __init__(self) -> None:
        self.children: dict[str, Node] = {}
        self.is_command = False


def build(names: list[str]) -> Node:
    root = Node()
    for name in names:
        node = root
        for letter in name:
            node = node.children.setdefault(letter, Node())
        node.is_command = True
    return root


def suggestions(root: Node, typed: str) -> tuple[list[str], int]:
    """The commands at most one changed letter away from `typed`, and how many nodes it visited."""
    found: list[str] = []
    visited = 0

    def visit(node: Node, depth: int, spelled: str, changes_left: int) -> None:
        nonlocal visited
        visited += 1
        if depth == len(typed):
            if node.is_command:
                found.append(spelled)
            return
        for letter, child in sorted(node.children.items()):
            if letter == typed[depth]:
                visit(child, depth + 1, spelled + letter, changes_left)
            elif changes_left > 0:  # branch: spend the one change on this letter
                visit(child, depth + 1, spelled + letter, changes_left - 1)

    visit(root, 0, "", changes_left=1)
    return found, visited


def by_comparing_every_command(typed: str) -> list[str]:
    return [
        name
        for name in sorted(COMMANDS)
        if len(name) == len(typed) and sum(a != b for a, b in zip(name, typed, strict=True)) <= 1
    ]


root = build(COMMANDS)
for typed in ("clome", "chesk", "lug", "logon", "clean", "bulid", "xyz"):
    found, visited = suggestions(root, typed)
    same = found == by_comparing_every_command(typed)
    print(f"{typed!r:<8} -> {found!s:<11} visited {visited:>2} nodes, matches a full scan: {same}")
