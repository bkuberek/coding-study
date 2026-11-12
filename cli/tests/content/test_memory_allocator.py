"""memory-allocator promises that its hidden cases catch the classic mistakes of a first heap
allocator: a block size without its header or its alignment, a split at the wrong threshold, a free
that accepts the wrong address, merging on the wrong side or at the wrong level, a fragmentation
figure computed the wrong way, placement policies that search, wrap or break ties wrongly, a
comparison that leaks into the allocator, and a buddy allocator that splits, chooses, merges or
counts its waste wrongly. These tests replay every case against a model of the allocator written
from the statement, which must give every expected output, and against that model with one mistake
planted at a time, which some hidden case must fail. The model keeps its blocks in a dictionary
keyed by address, and its next fit searches from the block that contains the rover, instead of
moving the rover when blocks merge as the reference does. A mistake that crashes fails its case, as
a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0383-memory-allocator"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

PLACEMENT = ["first-fit", "next-fit", "best-fit"]


class Model:
    """The allocator as the statement words it, one method per rule; each mistake overrides one.
    `blocks` maps a block's start to [size, used, requested]."""

    def __init__(self, heap_size: int) -> None:
        self.heap = heap_size
        self.blocks: dict[int, list[int]] = {0: [heap_size, 0, 0]}
        self.merging = False
        self.policy = "first-fit"
        self.touched = False
        self.rover = 0

    def starts(self) -> list[int]:
        return sorted(self.blocks)

    # --- level 1
    def need(self, size: int) -> int:
        if self.policy == "buddy":
            power = 16
            while power < size + 8:
                power *= 2
            return power
        return 8 + -(-size // 8) * 8

    def fits(self, need: int) -> list[int]:
        return [s for s in self.starts() if not self.blocks[s][1] and self.blocks[s][0] >= need]

    def pick(self, need: int) -> int | None:
        found = self.fits(need)
        if not found:
            return None
        if self.policy == "next-fit":
            return self.pick_next(found)
        if self.policy in ("best-fit", "buddy"):
            return self.pick_smallest(found)
        return found[0]

    def pick_smallest(self, found: list[int]) -> int:
        return min(found, key=lambda s: (self.blocks[s][0], s))

    def rover_block(self) -> int:
        return max(s for s in self.blocks if s <= self.rover)

    def pick_next(self, found: list[int]) -> int:
        here = self.rover_block()
        after = [s for s in found if s >= here]
        return after[0] if after else found[0]

    def should_split(self, spare: int) -> bool:
        return spare >= 16

    def place(self, start: int, need: int) -> None:
        size = self.blocks[start][0]
        if self.policy == "buddy":
            while size > need:
                size //= 2
                self.blocks[start][0] = size
                self.blocks[start + size] = [size, 0, 0]
        elif self.should_split(size - need):
            self.blocks[start][0] = need
            self.blocks[start + need] = [size - need, 0, 0]

    def address(self, start: int) -> int:
        return start + 8

    def allocate(self, size: int) -> int:
        self.touched = True
        need = self.need(size)
        start = self.pick(need)
        if start is None:
            return -1
        self.place(start, need)
        block = self.blocks[start]
        block[1], block[2] = 1, size
        self.rover = (start + block[0]) % self.heap
        return self.address(start)

    def owner(self, address: int) -> int | None:
        start = address - 8
        return start if start in self.blocks and self.blocks[start][1] else None

    def free(self, address: int) -> str:
        start = self.owner(address)
        if start is None:
            return "invalid"
        self.blocks[start][1] = 0
        if self.policy == "buddy":
            self.join_buddies(start)
        elif self.merging:
            self.coalesce(start)
        return "ok"

    def heap_map(self) -> list[str]:
        return [
            f"{s} {self.blocks[s][0]} {'used' if self.blocks[s][1] else 'free'}"
            for s in self.starts()
        ]

    # --- level 2
    def neighbors(self, start: int) -> tuple[int | None, int | None]:
        order = self.starts()
        at = order.index(start)
        before = order[at - 1] if at > 0 else None
        after = order[at + 1] if at + 1 < len(order) else None
        return before, after

    def absorb(self, start: int, other: int) -> None:
        self.blocks[start][0] += self.blocks.pop(other)[0]

    def coalesce(self, start: int) -> None:
        before, after = self.neighbors(start)
        if after is not None and not self.blocks[after][1]:
            self.absorb(start, after)
        if before is not None and not self.blocks[before][1]:
            self.absorb(before, start)

    def set_coalescing(self, enabled: bool) -> str:
        if self.touched:
            return "too-late"
        self.merging = enabled
        return "ok"

    def free_sizes(self) -> list[int]:
        return [size for size, used, _ in self.blocks.values() if not used]

    def share(self, total: int, largest: int) -> int:
        return (total - largest) * 100 // total if total else 0

    def free_report(self) -> list[int]:
        sizes = self.free_sizes()
        total, largest = sum(sizes), max(sizes, default=0)
        return [len(sizes), total, largest, self.share(total, largest)]

    # --- level 3
    def policy_status(self, policy: str) -> str | None:
        if policy not in [*PLACEMENT, "buddy"]:
            return "unknown-policy"
        if self.touched:
            return "too-late"
        if policy == "buddy" and self.heap & (self.heap - 1):
            return "bad-size"
        return None

    def set_policy(self, policy: str) -> str:
        status = self.policy_status(policy)
        if status is not None:
            return status
        self.policy = policy
        return "ok"

    def fresh(self, policy: str) -> "Model":
        other = type(self)(self.heap)
        other.merging = self.merging
        other.policy = policy
        return other

    def replay(self, heap: "Model", trace: list[int]) -> list[int]:
        returned: list[int] = []
        for step in trace:
            if step > 0:
                returned.append(heap.allocate(step))
            elif returned[-step - 1] != -1:
                heap.free(returned[-step - 1])
        return [returned.count(-1), *heap.free_report()]

    def compare(self, trace: list[int]) -> list[list[int]]:
        return [self.replay(self.fresh(policy), trace) for policy in PLACEMENT]

    # --- level 4
    def buddy_of(self, start: int) -> int:
        return start ^ self.blocks[start][0]

    def join_buddies(self, start: int) -> None:
        while self.blocks[start][0] < self.heap:
            mate = self.buddy_of(start)
            partner = self.blocks.get(mate)
            if partner is None or partner[1] or partner[0] != self.blocks[start][0]:
                return
            low, high = min(start, mate), max(start, mate)
            self.absorb(low, high)
            start = low

    def waste(self, size: int, requested: int) -> int:
        return size - 8 - requested

    def wasted(self) -> int:
        return sum(self.waste(size, req) for size, used, req in self.blocks.values() if used)


# ------------------------------------------------------------------ level 1 mistakes
class NoAlignment(Model):
    """Gives a block exactly the header and the bytes asked for."""

    def need(self, size: int) -> int:
        return super().need(size) if self.policy == "buddy" else 8 + size


class NoHeader(Model):
    """Forgets the header in the size of a block."""

    def need(self, size: int) -> int:
        return super().need(size) - 8 if self.policy != "buddy" else super().need(size)


class ReturnsTheBlockStart(Model):
    """Returns the start of the block instead of its payload."""

    def address(self, start: int) -> int:
        return start

    def owner(self, address: int) -> int | None:
        return super().owner(address + 8)


class SplitsAnyLeftover(Model):
    """Splits whenever something is left over."""

    def should_split(self, spare: int) -> bool:
        return spare > 0


class SplitsOnlyAboveSixteen(Model):
    """Splits only when more than 16 bytes are left over."""

    def should_split(self, spare: int) -> bool:
        return spare > 16


class NeverSplits(Model):
    """Hands out the whole free block every time."""

    def should_split(self, spare: int) -> bool:
        return False


class FreesTheBlockAroundTheAddress(Model):
    """Frees the used block that contains the address, wherever it points."""

    def owner(self, address: int) -> int | None:
        for start, (size, used, _) in self.blocks.items():
            if used and start < address <= start + size:
                return start
        return None


class FreeTwiceIsFine(Model):
    """Accepts freeing a block that is already free."""

    def free(self, address: int) -> str:
        if address - 8 in self.blocks and not self.blocks[address - 8][1]:
            return "ok"
        return super().free(address)


class AlwaysCoalesces(Model):
    """Merges free neighbors even when coalescing is off."""

    def free(self, address: int) -> str:
        self.merging = True
        return super().free(address)


class BestFitByDefault(Model):
    """Takes the smallest block that fits instead of the first one."""

    def pick(self, need: int) -> int | None:
        found = self.fits(need)
        if found and self.policy == "first-fit":
            return self.pick_smallest(found)
        return super().pick(need)


# ------------------------------------------------------------------ level 2 mistakes
class MergesOnlyForward(Model):
    """Merges a freed block with the next one only."""

    def coalesce(self, start: int) -> None:
        _, after = self.neighbors(start)
        if after is not None and not self.blocks[after][1]:
            self.absorb(start, after)


class MergesOnlyBackward(Model):
    """Merges a freed block with the previous one only."""

    def coalesce(self, start: int) -> None:
        before, _ = self.neighbors(start)
        if before is not None and not self.blocks[before][1]:
            self.absorb(before, start)


class MergesOneSide(Model):
    """Merges with the next block, or else with the previous one, never both."""

    def coalesce(self, start: int) -> None:
        before, after = self.neighbors(start)
        if after is not None and not self.blocks[after][1]:
            self.absorb(start, after)
        elif before is not None and not self.blocks[before][1]:
            self.absorb(before, start)


class FragmentationRoundsUp(Model):
    """Rounds the fragmentation percentage up."""

    def share(self, total: int, largest: int) -> int:
        return -(-(total - largest) * 100 // total) if total else 0


class FragmentationFromTheLargest(Model):
    """Reports the share of free memory inside the largest block."""

    def share(self, total: int, largest: int) -> int:
        return largest * 100 // total if total else 0


class FreeBytesWithoutHeaders(Model):
    """Counts only the payload of the free blocks."""

    def free_sizes(self) -> list[int]:
        return [size - 8 for size in super().free_sizes()]


class CoalescingAnyTime(Model):
    """Lets coalescing be switched on after the heap is in use."""

    def set_coalescing(self, enabled: bool) -> str:
        self.merging = enabled
        return "ok"


# ------------------------------------------------------------------ level 3 mistakes
class NextFitNeverWraps(Model):
    """Searches from the rover to the end of the heap only."""

    def pick_next(self, found: list[int]) -> int:
        here = self.rover_block()
        after = [s for s in found if s >= here]
        return after[0] if after else -1

    def pick(self, need: int) -> int | None:
        start = super().pick(need)
        return None if start == -1 else start


class NextFitFromTheStart(Model):
    """Restarts every search at address 0, which is first fit."""

    def pick_next(self, found: list[int]) -> int:
        return found[0]


class RoverLostInAMerge(Model):
    """Starts the search at the first block at or after the rover's old address."""

    def rover_block(self) -> int:
        later = [s for s in self.starts() if s >= self.rover]
        return later[0] if later else self.heap


class BestFitTiesToTheHighest(Model):
    """Breaks a tie between equal blocks toward the highest address."""

    def pick_smallest(self, found: list[int]) -> int:
        return min(found, key=lambda s: (self.blocks[s][0], -s))


class BestFitTakesTheLargest(Model):
    """Takes the largest block that fits."""

    def pick_smallest(self, found: list[int]) -> int:
        return max(found, key=lambda s: (self.blocks[s][0], -s))


class PolicyNamesIgnoreCase(Model):
    """Accepts policy names in any case."""

    def set_policy(self, policy: str) -> str:
        return super().set_policy(policy.lower())


class TooLateBeforeUnknown(Model):
    """Reports a late change before an unknown name."""

    def policy_status(self, policy: str) -> str | None:
        if self.touched:
            return "too-late"
        return super().policy_status(policy)


class CompareCountsFromZero(Model):
    """Reads `-k` as the request at index k."""

    def replay(self, heap: "Model", trace: list[int]) -> list[int]:
        returned: list[int] = []
        for step in trace:
            if step > 0:
                returned.append(heap.allocate(step))
            elif -step < len(returned) and returned[-step] != -1:
                heap.free(returned[-step])
        return [returned.count(-1), *heap.free_report()]


class CompareWithoutCoalescing(Model):
    """Replays the trace with coalescing off."""

    def fresh(self, policy: str) -> "Model":
        other = super().fresh(policy)
        other.merging = False
        return other


class CompareOnThisHeap(Model):
    """Replays the trace on this allocator, one policy after the other."""

    def fresh(self, policy: str) -> "Model":
        self.policy = policy
        return self


class CompareInAnotherOrder(Model):
    """Returns the rows best fit first."""

    def compare(self, trace: list[int]) -> list[list[int]]:
        return list(reversed(super().compare(trace)))


# ------------------------------------------------------------------ level 4 mistakes
class BuddyWithoutHeader(Model):
    """Rounds the request alone up to a power of two."""

    def need(self, size: int) -> int:
        if self.policy != "buddy":
            return super().need(size)
        power = 16
        while power < size:
            power *= 2
        return power


class BuddyKeepsTheUpperHalf(Model):
    """Uses the upper half of each split."""

    def place(self, start: int, need: int) -> None:
        if self.policy != "buddy":
            super().place(start, need)
            return
        size = self.blocks[start][0]
        while size > need:
            size //= 2
            self.blocks[start][0] = size
            self.blocks[start + size] = [size, 0, 0]
            start += size
        self.chosen = start

    def allocate(self, size: int) -> int:
        if self.policy != "buddy":
            return super().allocate(size)
        self.touched = True
        need = self.need(size)
        start = self.pick(need)
        if start is None:
            return -1
        self.place(start, need)
        block = self.blocks[self.chosen]
        block[1], block[2] = 1, size
        return self.address(self.chosen)


class BuddyTakesTheFirstFit(Model):
    """Splits the first free block that is large enough."""

    def pick(self, need: int) -> int | None:
        if self.policy == "buddy":
            found = self.fits(need)
            return found[0] if found else None
        return super().pick(need)


class BuddyMergesOnce(Model):
    """Merges a freed block with its buddy, and stops there."""

    def join_buddies(self, start: int) -> None:
        mate = self.buddy_of(start)
        partner = self.blocks.get(mate)
        if partner is not None and not partner[1] and partner[0] == self.blocks[start][0]:
            self.absorb(min(start, mate), max(start, mate))


class BuddyMergesAnyNeighbor(Model):
    """Merges with an adjacent free block of the same size, buddy or not."""

    def join_buddies(self, start: int) -> None:
        merged = True
        while merged:
            merged = False
            before, after = self.neighbors(start)
            size = self.blocks[start][0]
            for other in (after, before):
                if other is not None and self.blocks[other][:2] == [size, 0]:
                    low, high = min(start, other), max(start, other)
                    self.absorb(low, high)
                    start, merged = low, True
                    break


class BuddyFollowsCoalescing(Model):
    """Merges any free neighbors in the buddy system when coalescing is on."""

    def free(self, address: int) -> str:
        status = super().free(address)
        if status == "ok" and self.policy == "buddy" and self.merging:
            for start in self.starts():
                if start in self.blocks and not self.blocks[start][1]:
                    self.coalesce(start)
        return status


class BadSizeBeforeTooLate(Model):
    """Checks the heap size before the state of the heap."""

    def policy_status(self, policy: str) -> str | None:
        if policy == "buddy" and self.heap & (self.heap - 1):
            return "bad-size"
        return super().policy_status(policy)


class WasteIncludesTheHeader(Model):
    """Counts the header as wasted."""

    def waste(self, size: int, requested: int) -> int:
        return size - requested


class WasteOnlyInBuddies(Model):
    """Counts waste only for the buddy policy."""

    def wasted(self) -> int:
        return super().wasted() if self.policy == "buddy" else 0


class WasteCountsFreedBlocks(Model):
    """Keeps counting a block's waste after it is freed."""

    def wasted(self) -> int:
        return sum(self.waste(size, req) for size, _, req in self.blocks.values() if req)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_every_trace_frees_an_earlier_request_at_most_once():
    """The constraints promise that `-k` names a request made earlier in the trace, freed once."""
    traces = [
        arguments[0]
        for case in CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "compare"
    ]
    for trace in traces:
        requests, freed = 0, set()
        for step in trace:
            assert step != 0
            if step > 0:
                requests += 1
            else:
                assert -step <= requests, trace
                assert -step not in freed, trace
                freed.add(-step)


def test_the_policies_differ_on_the_compared_traces():
    """Level 3 promises that the policies give different results on the same trace."""
    rows = [
        tuple(map(tuple, result))
        for case in CASES
        for op, result in zip(case["ops"], case["expected"], strict=True)
        if op == "compare"
    ]
    assert any(len(set(row)) > 1 for row in rows)
