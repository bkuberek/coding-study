"""An arithmetic expression as a binary tree: operators inside, numbers at the leaves.

evaluate() sends values up: each operator combines the values its two subtrees return.
to_text() also sends state down: each call is told its parent's operator and which side of
it the call is on, which decides whether it needs parentheses."""

from dataclasses import dataclass


@dataclass
class Node:
    token: str  # "+", "-", "*" or a whole number
    left: "Node | None" = None
    right: "Node | None" = None


PRECEDENCE = {"+": 1, "-": 1, "*": 2}


def evaluate(node: Node, trace: list[str]) -> int:
    if node.token not in PRECEDENCE:  # a leaf: the answer is the number itself
        return int(node.token)
    left = evaluate(node.left, trace)  # trust the subtrees to answer for themselves
    right = evaluate(node.right, trace)
    value = {"+": left + right, "-": left - right, "*": left * right}[node.token]
    trace.append(f"{left} {node.token} {right} = {value}")
    return value


def to_text(node: Node, parent: str | None = None, side: str = "") -> str:
    if node.token not in PRECEDENCE:
        return node.token
    text = f"{to_text(node.left, node.token, 'left')} {node.token} "
    text += to_text(node.right, node.token, "right")
    if parent is None:
        return text
    weaker = PRECEDENCE[node.token] < PRECEDENCE[parent]
    # a - (b - c) and a - (b + c) need their parentheses; a + (b - c) does not
    regrouped = PRECEDENCE[node.token] == PRECEDENCE[parent] and parent == "-" and side == "right"
    return f"({text})" if weaker or regrouped else text


def leaf(number: int) -> Node:
    return Node(str(number))


# (7 - 2) * (1 + 3) - (6 - 1)
tree = Node(
    "-",
    Node("*", Node("-", leaf(7), leaf(2)), Node("+", leaf(1), leaf(3))),
    Node("-", leaf(6), leaf(1)),
)

steps: list[str] = []
result = evaluate(tree, steps)
for number, step in enumerate(steps, start=1):
    print(f"step {number}: {step}")
print("value:", result)
print("text: ", to_text(tree))
print("check:", eval(to_text(tree)) == result)  # Python's own parser agrees

# The same subtree, 3 - 1, below three different parents.
for operator in "+-*":
    print(f"under {operator}: {to_text(Node(operator, leaf(8), Node('-', leaf(3), leaf(1))))}")
