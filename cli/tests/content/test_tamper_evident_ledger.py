"""tamper-evident-ledger promises that its hidden cases catch the classic mistakes of a
hash-chained log: fields joined without lengths, lengths counted in characters, amounts left
unnormalized, digests that ignore order, chains that ignore their past, a search over the wrong
digests, and Merkle trees without prefixes or with the odd node promoted. These tests replay every
case against a model of the ledger written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from functools import reduce
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0311-tamper-evident-ledger"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
EMPTY_DIGEST = hashlib.sha256(b"").hexdigest()
ZERO_TIP = bytes(32)
HEX = re.compile(r"[0-9a-f]{64}")


def sha256(*parts: bytes) -> bytes:
    return hashlib.sha256(b"".join(parts)).digest()


def xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


class Model:
    """The ledger as the statement words it, one rule per method, so that each mistake below
    overrides a single method. Its methods take a call's arguments."""

    def __init__(self) -> None:
        self.batches: dict[str, list[list[str]]] = {}
        self.chains: dict[str, dict[str, Any]] = {}

    # --- the rules of the encoding
    def canonical(self, amount: str) -> str:
        if "." in amount:
            amount = amount.rstrip("0").rstrip(".")
        return "0" if amount == "-0" else amount

    def length(self, text: str) -> int:
        return len(text.encode("utf-8"))

    def prefix(self, count: int) -> bytes:
        return count.to_bytes(4, "big")

    def text(self, value: str) -> str:
        return value

    def field(self, value: str) -> bytes:
        value = self.text(value)
        return self.prefix(self.length(value)) + value.encode("utf-8")

    def record_bytes(self, record: Sequence[str]) -> bytes:
        record_id, sender, receiver, amount = record
        amount = self.canonical(amount)
        return b"".join(self.field(value) for value in (record_id, sender, receiver, amount))

    def record_digest(self, record: Sequence[str]) -> bytes:
        return sha256(self.record_bytes(record))

    def combine(self, digests: Sequence[bytes]) -> bytes:
        return sha256(*digests)

    def batch_digest_of(self, records: Sequence[Sequence[str]]) -> bytes:
        return self.combine([self.record_digest(record) for record in records])

    # --- level 1
    def add_batch(self, name: str, records: list[list[str]]) -> None:
        self.batches[name] = [list(record) for record in records]

    def batch_digest(self, name: str) -> str:
        return self.batch_digest_of(self.batches[name]).hex()

    def same_batch(self, first: str, second: str) -> bool:
        return self.batch_digest(first) == self.batch_digest(second)

    # --- level 2
    def new_chain(self, name: str, batch_size: int) -> None:
        self.chains[name] = {"size": batch_size, "pending": [], "sealed": [], "tips": []}

    def ready_to_seal(self, pending: Sequence[Any], size: int) -> bool:
        return len(pending) == size

    def chain_step(self, previous: bytes, batch_digest: bytes) -> bytes:
        return sha256(previous, batch_digest)

    def empty_tip(self) -> bytes:
        return ZERO_TIP

    def add_record(self, name: str, record: list[str]) -> None:
        chain = self.chains[name]
        chain["pending"].append(list(record))
        if self.ready_to_seal(chain["pending"], chain["size"]):
            batch = chain["pending"]
            chain["pending"] = []
            chain["sealed"].append(batch)
            previous = chain["tips"][-1] if chain["tips"] else self.empty_tip()
            chain["tips"].append(self.chain_step(previous, self.batch_digest_of(batch)))

    def sealed_count(self, name: str) -> int:
        return len(self.chains[name]["sealed"])

    def tip(self, name: str) -> bytes:
        tips = self.chains[name]["tips"]
        return tips[-1] if tips else self.empty_tip()

    def chain_digest(self, name: str) -> str:
        return self.tip(name).hex()

    def same_chain(self, first: str, second: str) -> bool:
        return self.tip(first) == self.tip(second)

    # --- level 3
    def prefix_marks(self, name: str) -> list[bytes]:
        return self.chains[name]["tips"]

    def common_prefix(self, first: str, second: str) -> int:
        left, right = self.prefix_marks(first), self.prefix_marks(second)
        low, high = 0, min(len(left), len(right))
        while low < high:
            middle = (low + high + 1) // 2
            if left[middle - 1] == right[middle - 1]:
                low = middle
            else:
                high = middle - 1
        return low

    # --- level 4
    def leaf(self, record_digest: bytes) -> bytes:
        return sha256(b"\x00", record_digest)

    def node(self, left: bytes, right: bytes) -> bytes:
        return sha256(b"\x01", left, right)

    def pair_up(self, level: list[bytes]) -> list[bytes]:
        padded = [*level, level[-1]] if len(level) % 2 else level
        return [self.node(padded[i], padded[i + 1]) for i in range(0, len(padded), 2)]

    def tree(self, records: Sequence[Sequence[str]]) -> list[list[bytes]]:
        levels = [[self.leaf(self.record_digest(record)) for record in records]]
        while len(levels[-1]) > 1:
            levels.append(self.pair_up(levels[-1]))
        return levels

    def merkle_root(self, name: str, batch_index: int) -> str:
        return self.tree(self.chains[name]["sealed"][batch_index])[-1][0].hex()

    def sibling_step(self, level: list[bytes], index: int) -> list[str]:
        padded = [*level, level[-1]] if len(level) % 2 else level
        sibling = index ^ 1
        return ["L" if sibling < index else "R", padded[sibling].hex()]

    def proof(self, name: str, batch_index: int, record_index: int) -> list[list[str]]:
        levels = self.tree(self.chains[name]["sealed"][batch_index])
        steps = []
        for depth, level in enumerate(levels[:-1]):
            steps.append(self.sibling_step(level, record_index >> depth))
        return steps

    def well_formed(self, step: Sequence[str]) -> bool:
        return len(step) == 2 and step[0] in ("L", "R") and HEX.fullmatch(step[1]) is not None

    def sibling_bytes(self, hex_text: str) -> bytes:
        return bytes.fromhex(hex_text)

    def verify_record(self, record: Sequence[str]) -> bytes:
        return self.leaf(self.record_digest(record))

    def roots_match(self, computed: bytes, root: str) -> bool:
        return computed.hex() == root

    def fold(self, current: bytes, step: Sequence[str]) -> bytes:
        sibling = self.sibling_bytes(step[1])
        return self.node(sibling, current) if step[0] == "L" else self.node(current, sibling)

    def verify(self, root: str, record: list[str], proof: list[list[str]]) -> bool:
        current = self.verify_record(record)
        for step in proof:
            if not self.well_formed(step):
                return False
            current = self.fold(current, step)
        return self.roots_match(current, root)


# ------------------------------------------------------------------ level 1 mistakes
class JoinedWithoutLengths(Model):
    """Hashes `id + sender + receiver + amount` as one text."""

    def record_bytes(self, record: Sequence[str]) -> bytes:
        record_id, sender, receiver, amount = record
        return (record_id + sender + receiver + self.canonical(amount)).encode("utf-8")


class JoinedWithSeparator(Model):
    """Joins the fields with a `|`, which a field may hold."""

    def record_bytes(self, record: Sequence[str]) -> bytes:
        record_id, sender, receiver, amount = record
        return "|".join([record_id, sender, receiver, self.canonical(amount)]).encode("utf-8")


class LengthInCharacters(Model):
    """Counts the characters of a field, not its bytes."""

    def length(self, text: str) -> int:
        return len(text)


class LengthInUtf16Units(Model):
    """Counts UTF-16 code units, as `String.length` does in JavaScript and Java."""

    def length(self, text: str) -> int:
        return len(text.encode("utf-16-le")) // 2


class LittleEndianLength(Model):
    """Writes the length with the low byte first."""

    def prefix(self, count: int) -> bytes:
        return count.to_bytes(4, "little")


class AmountNotCanonical(Model):
    """Hashes the amount as written."""

    def canonical(self, amount: str) -> str:
        return amount


class EveryTrailingZeroStripped(Model):
    """Strips the zeros of `100` too, which makes `1`, `10` and `100` the same amount."""

    def canonical(self, amount: str) -> str:
        stripped = amount.rstrip("0").rstrip(".") if "." in amount else amount.rstrip("0")
        return stripped or "0"


class NegativeZeroKept(Model):
    """Leaves `-0` and `-0.0` as they are."""

    def canonical(self, amount: str) -> str:
        return amount.rstrip("0").rstrip(".") if "." in amount else amount


class FractionZerosKeptWhenOne(Model):
    """Strips the fractional zeros but leaves the point: `1.0` becomes `1.`."""

    def canonical(self, amount: str) -> str:
        if "." in amount:
            amount = amount.rstrip("0")
        return "0" if amount == "-0" else amount


class UnicodeNormalized(Model):
    """Normalizes text to NFC before hashing it."""

    def text(self, value: str) -> str:
        return unicodedata.normalize("NFC", value)


class TextCaseFolded(Model):
    """Compares text without its case."""

    def text(self, value: str) -> str:
        return value.lower()


class RecordsSorted(Model):
    """Sorts the record digests, so the order of the records stops mattering."""

    def combine(self, digests: Sequence[bytes]) -> bytes:
        return sha256(*sorted(digests))


class RecordsDeduplicated(Model):
    """Keeps a record once, as a set would."""

    def combine(self, digests: Sequence[bytes]) -> bytes:
        return sha256(*sorted(set(digests)))


class RecordDigestsXored(Model):
    """Combines the record digests with xor, which is order-blind and cancels repeats."""

    def combine(self, digests: Sequence[bytes]) -> bytes:
        total = reduce(xor_bytes, digests, bytes(32))
        return sha256(total)


class HexTextHashed(Model):
    """Hashes the hexadecimal text of the record digests instead of the bytes."""

    def combine(self, digests: Sequence[bytes]) -> bytes:
        return sha256(*(digest.hex().encode("ascii") for digest in digests))


class FirstRecordOnly(Model):
    """Fingerprints the batch by its first record."""

    def combine(self, digests: Sequence[bytes]) -> bytes:
        return sha256(*digests[:1])


# ------------------------------------------------------------------ level 2 mistakes
class PendingRecordsCount(Model):
    """Compares the pending records too."""

    def same_chain(self, first: str, second: str) -> bool:
        return super().same_chain(first, second) and (
            self.chains[first]["pending"] == self.chains[second]["pending"]
        )


class OnlyTheLastBatchCounts(Model):
    """The chain digest is the last batch's digest, with no previous digest in it."""

    def chain_step(self, previous: bytes, batch_digest: bytes) -> bytes:
        return batch_digest


class ChainStartsFromNothing(Model):
    """Starts from an empty input instead of 32 zero bytes."""

    def empty_tip(self) -> bytes:
        return b""


class ChainOfAnEmptyChainIsEmptyHash(Model):
    """Reports the digest of nothing for a chain with no sealed batch."""

    def tip(self, name: str) -> bytes:
        tips = self.chains[name]["tips"]
        return tips[-1] if tips else sha256()


class BatchSizeCompared(Model):
    """Counts the batch size as part of a chain, so empty chains of two sizes differ."""

    def same_chain(self, first: str, second: str) -> bool:
        same_size = self.chains[first]["size"] == self.chains[second]["size"]
        return super().same_chain(first, second) and same_size


class SealsOneRecordLate(Model):
    """Seals when a batch holds one record more than its size."""

    def ready_to_seal(self, pending: Sequence[Any], size: int) -> bool:
        return len(pending) == size + 1


class SealsEarly(Model):
    """Seals a batch when it is one record short."""

    def ready_to_seal(self, pending: Sequence[Any], size: int) -> bool:
        return len(pending) == max(size - 1, 1)


class ChainDigestIsAnXor(Model):
    """Xors the batch digests, so the order of the batches stops mattering."""

    def chain_step(self, previous: bytes, batch_digest: bytes) -> bytes:
        return xor_bytes(previous, batch_digest)


class ChainStepHashesHexText(Model):
    """Hashes the hexadecimal text of the two digests."""

    def chain_step(self, previous: bytes, batch_digest: bytes) -> bytes:
        return sha256(previous.hex().encode("ascii"), batch_digest.hex().encode("ascii"))


# ------------------------------------------------------------------ level 3 mistakes
class PrefixOverBatchDigests(Model):
    """Bisects over the digests of single batches, which are not a prefix property."""

    def prefix_marks(self, name: str) -> list[bytes]:
        return [self.batch_digest_of(batch) for batch in self.chains[name]["sealed"]]


class PrefixCountsMatchingPositions(Model):
    """Counts the positions at which the batches agree, wherever they are."""

    def common_prefix(self, first: str, second: str) -> int:
        left, right = self.chains[first]["sealed"], self.chains[second]["sealed"]
        return sum(a == b for a, b in zip(left, right, strict=False))


class PrefixNeverFull(Model):
    """Leaves the last batch out of the search."""

    def common_prefix(self, first: str, second: str) -> int:
        left, right = self.prefix_marks(first), self.prefix_marks(second)
        low, high = 0, max(min(len(left), len(right)) - 1, 0)
        while low < high:
            middle = (low + high + 1) // 2
            if left[middle - 1] == right[middle - 1]:
                low = middle
            else:
                high = middle - 1
        return low


class PrefixStopsAtTheFirstBatch(Model):
    """Answers 0 or 1 by looking at the first batch only."""

    def common_prefix(self, first: str, second: str) -> int:
        left, right = self.prefix_marks(first), self.prefix_marks(second)
        return 1 if left and right and left[0] == right[0] else 0


class PrefixComparesEnds(Model):
    """Returns the shorter length when the last digests agree, and 0 otherwise."""

    def common_prefix(self, first: str, second: str) -> int:
        left, right = self.prefix_marks(first), self.prefix_marks(second)
        shorter = min(len(left), len(right))
        return shorter if shorter and left[shorter - 1] == right[shorter - 1] else 0


# ------------------------------------------------------------------ level 4 mistakes
class NoPrefixes(Model):
    """Hashes leaves and nodes without the 0x00 and 0x01 bytes."""

    def leaf(self, record_digest: bytes) -> bytes:
        return sha256(record_digest)

    def node(self, left: bytes, right: bytes) -> bytes:
        return sha256(left, right)


class SamePrefixForLeavesAndNodes(Model):
    """Gives leaves and nodes the same prefix byte."""

    def leaf(self, record_digest: bytes) -> bytes:
        return sha256(b"\x01", record_digest)


class OddNodePromoted(Model):
    """Carries the last node of an odd level up unchanged, instead of pairing it with a copy."""

    def pair_up(self, level: list[bytes]) -> list[bytes]:
        pairs = [self.node(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        return [*pairs, level[-1]] if len(level) % 2 else pairs

    def sibling_step(self, level: list[bytes], index: int) -> list[str]:
        sibling = index ^ 1
        if sibling >= len(level):
            return ["R", level[index].hex()]
        return ["L" if sibling < index else "R", level[sibling].hex()]


class OddNodeDuplicatedOnlyOnce(Model):
    """Pads the leaves but not the levels above them."""

    def pair_up(self, level: list[bytes]) -> list[bytes]:
        padded = [*level, level[-1]] if len(level) % 2 and len(level) == 3 else level
        pairs = [self.node(padded[i], padded[i + 1]) for i in range(0, len(padded) - 1, 2)]
        return [*pairs, padded[-1]] if len(padded) % 2 else pairs

    def sibling_step(self, level: list[bytes], index: int) -> list[str]:
        padded = [*level, level[-1]] if len(level) % 2 else level
        return ["L" if (index ^ 1) < index else "R", padded[index ^ 1].hex()]


class SidesSwapped(Model):
    """Names the sibling's side from the other point of view."""

    def sibling_step(self, level: list[bytes], index: int) -> list[str]:
        side, digest = super().sibling_step(level, index)
        return ["R" if side == "L" else "L", digest]

    def fold(self, current: bytes, step: Sequence[str]) -> bytes:
        sibling = self.sibling_bytes(step[1])
        return self.node(current, sibling) if step[0] == "L" else self.node(sibling, current)


class VerifyIgnoresSide(Model):
    """Always puts the sibling on the right."""

    def fold(self, current: bytes, step: Sequence[str]) -> bytes:
        return self.node(current, self.sibling_bytes(step[1]))


class VerifyWithoutCanonicalAmount(Model):
    """Rebuilds the leaf from the amount as written."""

    def verify_record(self, record: Sequence[str]) -> bytes:
        record_id, sender, receiver, amount = record
        raw = b"".join(self.field(value) for value in (record_id, sender, receiver, amount))
        return self.leaf(sha256(raw))


class VerifyAcceptsAnyHex(Model):
    """Lets a lenient hexadecimal parser decide what a hash is."""

    def well_formed(self, step: Sequence[str]) -> bool:
        if len(step) != 2 or step[0] not in ("L", "R"):
            return False
        try:
            return len(bytes.fromhex(step[1])) == 32
        except ValueError:
            return False


class VerifyAcceptsAnySide(Model):
    """Treats every side that is not `L` as right."""

    def well_formed(self, step: Sequence[str]) -> bool:
        return len(step) == 2 and HEX.fullmatch(step[1]) is not None


class VerifyIgnoresStepLength(Model):
    """Reads the first two entries of a step and ignores the rest."""

    def well_formed(self, step: Sequence[str]) -> bool:
        return len(step) >= 2 and step[0] in ("L", "R") and HEX.fullmatch(step[1]) is not None


class VerifyComparesRootLoosely(Model):
    """Compares the root without its case."""

    def roots_match(self, computed: bytes, root: str) -> bool:
        return computed.hex() == root.lower()


class VerifyAcceptsAnyPrefixOfTheRoot(Model):
    """Compares only the first 16 characters of the root."""

    def roots_match(self, computed: bytes, root: str) -> bool:
        return computed.hex()[:16] == root[:16]


class VerifyStopsAtTheFirstStep(Model):
    """Applies only the first step of the proof."""

    def verify(self, root: str, record: list[str], proof: list[list[str]]) -> bool:
        return super().verify(root, record, proof[:1])


class SingleRecordProofNotEmpty(Model):
    """Gives a batch of one record a step, pairing the leaf with itself."""

    def tree(self, records: Sequence[Sequence[str]]) -> list[list[bytes]]:
        levels = super().tree(records)
        if len(levels) == 1:
            leaf = levels[0][0]
            return [levels[0], [self.node(leaf, leaf)]]
        return levels


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_the_digest_of_an_empty_batch_is_the_digest_of_nothing():
    empty = next(case for case in CASES if case["id"] == "h7")
    assert EMPTY_DIGEST in empty["expected"]


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
