"""A Merkle tree with inclusion proofs, as RFC 9162 defines them for Certificate Transparency.

A leaf is SHA-256(0x00 || data); a node is SHA-256(0x01 || left || right). A list of n > 1 items
splits at k, the largest power of two smaller than n, so an odd item is never duplicated.
"""

import hashlib

LEAF, NODE = b"\x00", b"\x01"


def sha256(*parts: bytes) -> bytes:
    return hashlib.sha256(b"".join(parts)).digest()


def split(n: int) -> int:
    """The largest power of two smaller than n, for n > 1."""
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def root(items: list[bytes]) -> bytes:
    if len(items) == 1:
        return sha256(LEAF, items[0])
    k = split(len(items))
    return sha256(NODE, root(items[:k]), root(items[k:]))


def proof(index: int, items: list[bytes]) -> list[tuple[str, bytes]]:
    """The siblings from the leaf up: ('L', hash) when the sibling is on the left."""
    if len(items) == 1:
        return []
    k = split(len(items))
    if index < k:
        return [*proof(index, items[:k]), ("R", root(items[k:]))]
    return [*proof(index - k, items[k:]), ("L", root(items[:k]))]


def verify(expected_root: bytes, item: bytes, steps: list[tuple[str, bytes]]) -> bool:
    node = sha256(LEAF, item)
    for side, sibling in steps:
        node = sha256(NODE, sibling, node) if side == "L" else sha256(NODE, node, sibling)
    return node == expected_root


files = [b"photo-01.jpg", b"photo-02.jpg", b"notes.txt", b"budget.ods", b"cv.pdf"]
published = root(files)
steps = proof(2, files)
print("files:", len(files), "| proof for notes.txt has", len(steps), "steps:", [s for s, _ in steps])
print("notes.txt verifies:", verify(published, b"notes.txt", steps))
print("a changed file verifies:", verify(published, b"notes.txt!", steps))
print("cv.pdf, the odd one, needs", len(proof(4, files)), "step(s):", verify(published, b"cv.pdf", proof(4, files)))

# Without the 0x00 and 0x01 prefixes, a node's two children, concatenated, would be accepted as a
# leaf whose data is those 64 bytes: the prefixes keep leaves and nodes apart.
inner = sha256(LEAF, files[0]) + sha256(LEAF, files[1])
print("a node's 64 child bytes hashed as a leaf match the node:", sha256(LEAF, inner) == sha256(NODE, inner))
