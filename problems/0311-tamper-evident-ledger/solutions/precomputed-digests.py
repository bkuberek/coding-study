import hashlib
import re

GENESIS = bytes(32)
LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


def sha256(*parts: bytes) -> bytes:
    return hashlib.sha256(b"".join(parts)).digest()


def encode_text(value: str) -> bytes:
    """A field is its length in bytes (4 bytes, big-endian) and then its UTF-8 bytes."""
    data = value.encode("utf-8")
    return len(data).to_bytes(4, "big") + data


def canonical_amount(amount: str) -> str:
    """Drops trailing fractional zeros and a dangling point, and writes `-0` as `0`."""
    if "." in amount:
        amount = amount.rstrip("0").rstrip(".")
    return "0" if amount == "-0" else amount


def record_digest(record: list[str]) -> bytes:
    record_id, sender, receiver, amount = record
    return sha256(
        encode_text(record_id),
        encode_text(sender),
        encode_text(receiver),
        encode_text(canonical_amount(amount)),
    )


def leaf_digest(digest_of_record: bytes) -> bytes:
    return sha256(LEAF_PREFIX, digest_of_record)


def node_digest(left: bytes, right: bytes) -> bytes:
    return sha256(NODE_PREFIX, left, right)


class Batch:
    """Everything a batch can be asked is computed once, when it is built."""

    def __init__(self, records: list[list[str]]) -> None:
        self.record_digests = [record_digest(record) for record in records]
        self.digest = sha256(*self.record_digests)
        self._levels: list[list[bytes]] | None = None

    def levels(self) -> list[list[bytes]]:
        """The Merkle tree from the leaves up; a level of odd length is padded when it is paired."""
        if self._levels is None:
            level = [leaf_digest(digest) for digest in self.record_digests]
            self._levels = [level]
            while len(level) > 1:
                padded = level + [level[-1]] if len(level) % 2 else level
                level = [node_digest(padded[i], padded[i + 1]) for i in range(0, len(padded), 2)]
                self._levels.append(level)
        return self._levels

    def root(self) -> bytes:
        return self.levels()[-1][0]

    def proof(self, record_index: int) -> list[list[str]]:
        steps: list[list[str]] = []
        index = record_index
        for level in self.levels()[:-1]:
            padded = level + [level[-1]] if len(level) % 2 else level
            sibling = index ^ 1
            side = "L" if sibling < index else "R"
            steps.append([side, padded[sibling].hex()])
            index //= 2
        return steps


class Chain:
    def __init__(self, batch_size: int) -> None:
        self.batch_size = batch_size
        self.pending: list[list[str]] = []
        self.batches: list[Batch] = []
        self.digests: list[bytes] = []

    def add(self, record: list[str]) -> None:
        self.pending.append(record)
        if len(self.pending) == self.batch_size:
            batch = Batch(self.pending)
            self.pending = []
            self.batches.append(batch)
            self.digests.append(sha256(self.tip(), batch.digest))

    def tip(self) -> bytes:
        return self.digests[-1] if self.digests else GENESIS


class Ledger:
    def __init__(self) -> None:
        self._batches: dict[str, Batch] = {}
        self._chains: dict[str, Chain] = {}

    # Level 1
    def add_batch(self, name: str, records: list[list[str]]) -> None:
        self._batches[name] = Batch(records)

    def batch_digest(self, name: str) -> str:
        return self._batches[name].digest.hex()

    def same_batch(self, first: str, second: str) -> bool:
        return self._batches[first].digest == self._batches[second].digest

    # Level 2
    def new_chain(self, name: str, batch_size: int) -> None:
        self._chains[name] = Chain(batch_size)

    def add_record(self, name: str, record: list[str]) -> None:
        self._chains[name].add(record)

    def sealed_count(self, name: str) -> int:
        return len(self._chains[name].batches)

    def chain_digest(self, name: str) -> str:
        return self._chains[name].tip().hex()

    def same_chain(self, first: str, second: str) -> bool:
        return self._chains[first].tip() == self._chains[second].tip()

    # Level 3
    def common_prefix(self, first: str, second: str) -> int:
        """The prefix digests agree up to some length and never again, so the length can be bisected."""
        left, right = self._chains[first].digests, self._chains[second].digests
        low, high = 0, min(len(left), len(right))
        while low < high:
            middle = (low + high + 1) // 2
            if left[middle - 1] == right[middle - 1]:
                low = middle
            else:
                high = middle - 1
        return low

    # Level 4
    def merkle_root(self, name: str, batch_index: int) -> str:
        return self._chains[name].batches[batch_index].root().hex()

    def proof(self, name: str, batch_index: int, record_index: int) -> list[list[str]]:
        return self._chains[name].batches[batch_index].proof(record_index)

    def verify(self, root: str, record: list[str], proof: list[list[str]]) -> bool:
        current = leaf_digest(record_digest(record))
        for step in proof:
            if len(step) != 2 or step[0] not in ("L", "R") or not HEX_DIGEST.fullmatch(step[1]):
                return False
            sibling = bytes.fromhex(step[1])
            current = node_digest(sibling, current) if step[0] == "L" else node_digest(current, sibling)
        return current.hex() == root
