from collections.abc import Iterator

from cs_support import TreeNode

MISSING = "#"
SEPARATOR = ","


def serialize_deserialize(root: TreeNode | None) -> TreeNode | None:
    return deserialize(serialize(root))


def serialize(root: TreeNode | None) -> str:
    tokens: list[str] = []

    def write(node: TreeNode | None) -> None:
        if node is None:
            tokens.append(MISSING)
            return
        tokens.append(str(node.val))
        write(node.left)
        write(node.right)

    write(root)
    return SEPARATOR.join(tokens)


def deserialize(data: str) -> TreeNode | None:
    tokens: Iterator[str] = iter(data.split(SEPARATOR))

    def read() -> TreeNode | None:
        token = next(tokens)
        if token == MISSING:
            return None
        node = TreeNode(int(token))
        node.left = read()
        node.right = read()
        return node

    return read()
