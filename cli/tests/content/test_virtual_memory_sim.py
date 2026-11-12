"""virtual-memory-sim promises that its hidden cases catch the classic mistakes of simulating paged
virtual memory: page number and offset swapped or split at the wrong bit, a fault that is not
counted, a TLB that is not least recently used, keeps a stale entry after a mapping changes, or
counts a fault the wrong way, a replacement policy that forgets a use, a clock that gives no
second chance or loses its place, tables counted by page instead of by table, and a working set
or thrashing rule off by one. These tests replay every case against a model of the memory
written from the statement, which must give every expected output, and against that model with
one mistake planted at a time, which some hidden case must fail. A mistake that crashes fails
its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0360-virtual-memory-sim"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


class Model:
    """The memory as the statement words it, kept in plain lists: the TLB is a list of
    `[page, frame]` from the least to the most recently used entry, the frames are a list of the
    page each holds, and the policies read a clock of references: when each page was loaded and
    when it was last used. Each mistake below overrides one rule."""

    def __init__(self, page_size: int) -> None:
        self.size = page_size
        self.table: dict[int, int] = {}
        self.fault_count = 0
        self.tlb: list[list[int]] | None = None
        self.tlb_size = 0
        self.hits = 0
        self.misses = 0
        self.frames: list[int | None] = []
        self.policy = ""
        self.loaded_at: dict[int, int] = {}
        self.used_at: dict[int, int] = {}
        self.use_bit: list[bool] = []
        self.hand = 0
        self.history: list[int] = []

    # --- level 1
    def split(self, address: int) -> list[int]:
        return [address // self.size, address % self.size]

    def map_page(self, page: int, frame: int) -> bool:
        new = page not in self.table
        self.table[page] = frame
        self.drop_from_tlb(page)
        return new

    def unmap_page(self, page: int) -> bool:
        if page not in self.table:
            return False
        del self.table[page]
        self.drop_from_tlb(page)
        return True

    def physical(self, frame: int, offset: int) -> int:
        return frame * self.size + offset

    def translate(self, address: int) -> int:
        page, offset = self.split(address)
        self.reference(page)
        frame = self.find(page)
        return -1 if frame is None else self.physical(frame, offset)

    def reference(self, page: int) -> None:
        self.history.append(page)

    def faults(self) -> int:
        return self.fault_count

    def count_fault(self, page: int) -> None:
        self.fault_count += 1

    # --- level 2
    def enable_tlb(self, entries: int) -> None:
        self.tlb = []
        self.tlb_size = entries
        self.hits = self.misses = 0

    def flush_tlb(self) -> None:
        if self.tlb is not None:
            self.tlb = []

    def tlb_hits(self) -> int:
        return self.hits

    def tlb_misses(self) -> int:
        return self.misses

    def drop_from_tlb(self, page: int) -> None:
        if self.tlb is not None:
            self.tlb = [entry for entry in self.tlb if entry[0] != page]

    def entries(self) -> list[list[int]]:
        """The TLB's entries, for the methods that only run with a TLB."""
        assert self.tlb is not None
        return self.tlb

    def tlb_hit(self, page: int) -> int | None:
        tlb = self.tlb or []
        for entry in tlb:
            if entry[0] == page:
                tlb.remove(entry)
                tlb.append(entry)
                return entry[1]
        return None

    def tlb_add(self, page: int, frame: int) -> None:
        tlb = self.entries()
        if len(tlb) >= self.tlb_size:
            tlb.pop(0)
        tlb.append([page, frame])

    def find(self, page: int) -> int | None:
        if self.tlb is not None:
            frame = self.tlb_hit(page)
            if frame is not None:
                self.hits += 1
                self.used(page, hit=True)
                return frame
            self.misses += 1
        frame = self.table.get(page)
        if frame is None:
            self.count_fault(page)
            if not self.frames:
                return None
            frame = self.bring_in(page)
        self.used(page, hit=False)
        if self.tlb is not None:
            self.tlb_add(page, frame)
        return frame

    # --- level 3
    def use_frames(self, count: int, policy: str) -> None:
        self.frames = [None] * count
        self.policy = policy
        self.table = {}
        self.flush_tlb()
        self.fault_count = self.hits = self.misses = 0
        self.loaded_at, self.used_at = {}, {}
        self.use_bit = [False] * count
        self.hand = 0
        self.forget_history()

    def forget_history(self) -> None:
        self.history = []

    def resident(self) -> list[int]:
        return sorted(self.table)

    def used(self, page: int, hit: bool) -> None:
        if not self.frames:
            return
        self.used_at[page] = len(self.history)
        self.use_bit[self.table[page]] = True

    def free_frame(self) -> int | None:
        return next((f for f, p in enumerate(self.frames) if p is None), None)

    def fifo_victim(self) -> int:
        return min(self.table, key=lambda p: self.loaded_at[p])

    def lru_victim(self) -> int:
        return min(self.table, key=lambda p: self.used_at[p])

    def clock_frame(self) -> int:
        while self.use_bit[self.hand]:
            self.use_bit[self.hand] = False
            self.hand = (self.hand + 1) % len(self.frames)
        frame = self.hand
        self.hand = (self.hand + 1) % len(self.frames)
        return frame

    def victim_frame(self) -> int:
        if self.policy == "fifo":
            return self.table[self.fifo_victim()]
        if self.policy == "lru":
            return self.table[self.lru_victim()]
        return self.clock_frame()

    def page_in(self, frame: int) -> int:
        page = self.frames[frame]
        assert page is not None
        return page

    def evict(self, frame: int) -> None:
        victim = self.page_in(frame)
        del self.table[victim]
        self.drop_from_tlb(victim)

    def bring_in(self, page: int) -> int:
        frame = self.free_frame()
        if frame is None:
            frame = self.victim_frame()
            self.evict(frame)
        self.frames[frame] = page
        self.table[page] = frame
        self.loaded_at[page] = len(self.history)
        return frame

    # --- level 4
    def per_table(self, entry_bytes: int) -> int:
        return self.size // entry_bytes

    def walk(self, address: int, entry_bytes: int) -> list[int]:
        page, offset = self.split(address)
        per = self.per_table(entry_bytes)
        return [page // per, page % per, offset]

    def pages_in(self, address_bits: int) -> int:
        return 2**address_bits // self.size

    def table_bytes(self, address_bits: int, entry_bytes: int) -> list[int]:
        pages = self.pages_in(address_bits)
        per = self.per_table(entry_bytes)
        directory = pages // per * entry_bytes
        tables = len({page // per for page in self.table})
        return [pages * entry_bytes, directory + tables * self.size]

    def window(self, window: int) -> list[int]:
        return self.history[-window:]

    def working_set(self, window: int) -> list[int]:
        return sorted(set(self.window(window)))

    def too_many(self, pages: int) -> bool:
        return bool(self.frames) and pages > len(self.frames)

    def thrashing(self, window: int) -> bool:
        return self.too_many(len(self.working_set(window)))


# ------------------------------------------------------------------ level 1 mistakes
class OffsetFromTheTop(Model):
    """Takes the page number from the low bits and the offset from the high bits."""

    def split(self, address: int) -> list[int]:
        page, offset = super().split(address)
        return [offset, page]


class SplitOneBitOff(Model):
    """Splits the address one bit too low, as if pages were half as big."""

    def split(self, address: int) -> list[int]:
        half = self.size // 2
        return [address // half, address % half]


class FrameNotScaled(Model):
    """Adds the offset to the frame number instead of to the frame's first byte."""

    def physical(self, frame: int, offset: int) -> int:
        return frame + offset


class RemapReturnsTrue(Model):
    """Says a mapping is new even when it replaces one."""

    def map_page(self, page: int, frame: int) -> bool:
        super().map_page(page, frame)
        return True


class UnmapAlwaysTrue(Model):
    """Says it removed a mapping that was not there."""

    def unmap_page(self, page: int) -> bool:
        super().unmap_page(page)
        return True


class FaultOncePerPage(Model):
    """Counts a fault only the first time a page faults."""

    def count_fault(self, page: int) -> None:
        seen = self.__dict__.setdefault("faulted", set())
        if page not in seen:
            seen.add(page)
            self.fault_count += 1


class AddressesAs32Bits(Model):
    """Keeps addresses in 32 bits."""

    def split(self, address: int) -> list[int]:
        return super().split(address % 2**32)


# ------------------------------------------------------------------ level 2 mistakes
class TlbFirstInFirstOut(Model):
    """Evicts the oldest TLB entry, even if it was just used."""

    def tlb_hit(self, page: int) -> int | None:
        for entry in self.tlb or []:
            if entry[0] == page:
                return entry[1]
        return None


class TlbEvictsTheNewest(Model):
    """Evicts the most recently used TLB entry."""

    def tlb_add(self, page: int, frame: int) -> None:
        tlb = self.entries()
        if len(tlb) >= self.tlb_size:
            tlb.pop()
        tlb.append([page, frame])


class TlbOneEntryShort(Model):
    """Evicts while the TLB still has a free entry."""

    def tlb_add(self, page: int, frame: int) -> None:
        tlb = self.entries()
        if len(tlb) >= self.tlb_size - 1 and tlb:
            tlb.pop(0)
        tlb.append([page, frame])


class RemapKeepsTheEntry(Model):
    """Leaves the TLB alone when a page is mapped again."""

    def map_page(self, page: int, frame: int) -> bool:
        new = page not in self.table
        self.table[page] = frame
        return new


class UnmapKeepsTheEntry(Model):
    """Leaves the TLB alone when a page is unmapped."""

    def unmap_page(self, page: int) -> bool:
        if page not in self.table:
            return False
        del self.table[page]
        return True


class FaultIsNotAMiss(Model):
    """Counts a fault, but not the TLB miss that led to it."""

    def count_fault(self, page: int) -> None:
        super().count_fault(page)
        if self.tlb is not None:
            self.misses -= 1


class FlushResetsTheCounts(Model):
    """Resets the hit and miss counts when the TLB is flushed."""

    def flush_tlb(self) -> None:
        super().flush_tlb()
        self.hits = self.misses = 0


class EnableKeepsTheCounts(Model):
    """Keeps the hit and miss counts when a TLB is enabled again."""

    def enable_tlb(self, entries: int) -> None:
        hits, misses = self.hits, self.misses
        super().enable_tlb(entries)
        self.hits, self.misses = hits, misses


class MissesWithoutATlb(Model):
    """Counts a miss for every translation when there is no TLB."""

    def find(self, page: int) -> int | None:
        if self.tlb is None:
            self.misses += 1
        return super().find(page)


# ------------------------------------------------------------------ level 3 mistakes
class LruOnlyCountsLoads(Model):
    """Records when a page was loaded and calls it its last use."""

    def used(self, page: int, hit: bool) -> None:
        if not self.frames:
            return
        self.used_at.setdefault(page, len(self.history))
        self.use_bit[self.table[page]] = True

    def evict(self, frame: int) -> None:
        self.used_at.pop(self.page_in(frame), None)
        super().evict(frame)


class TlbHitsAreNotUses(Model):
    """Updates the replacement state only on a TLB miss."""

    def used(self, page: int, hit: bool) -> None:
        if not hit:
            super().used(page, hit)


class ClockWithoutSecondChance(Model):
    """Never looks at the use bits: the clock becomes first in, first out."""

    def clock_frame(self) -> int:
        frame = self.hand
        self.hand = (self.hand + 1) % len(self.frames)
        return frame


class ClockHandStaysOnTheNewPage(Model):
    """Leaves the hand on the frame it just filled."""

    def clock_frame(self) -> int:
        frame = super().clock_frame()
        self.hand = frame
        return frame


class ClockLoadsWithoutTheUseBit(Model):
    """Loads a page with its use bit clear."""

    def bring_in(self, page: int) -> int:
        frame = super().bring_in(page)
        self.fresh = [frame]
        return frame

    def used(self, page: int, hit: bool) -> None:
        super().used(page, hit)
        for frame in getattr(self, "fresh", []):
            self.use_bit[frame] = False
        self.fresh = []


class EvictedPageStaysInTheTlb(Model):
    """Evicts a page from memory but not from the TLB."""

    def evict(self, frame: int) -> None:
        del self.table[self.page_in(frame)]


class NewEntryBeforeTheVictimLeaves(Model):
    """Adds the new page to the TLB before removing the victim's entry."""

    def find(self, page: int) -> int | None:
        self.pending: list[int] = []
        frame = super().find(page)
        for victim in self.pending:
            Model.drop_from_tlb(self, victim)
        return frame

    def evict(self, frame: int) -> None:
        victim = self.page_in(frame)
        del self.table[victim]
        self.pending.append(victim)


class FreeFramesFromTheTop(Model):
    """Fills the highest free frame first."""

    def free_frame(self) -> int | None:
        free = [f for f, p in enumerate(self.frames) if p is None]
        return free[-1] if free else None


class UseFramesKeepsTheCounts(Model):
    """Keeps the fault, hit and miss counts of the previous run."""

    def use_frames(self, count: int, policy: str) -> None:
        kept = (self.fault_count, self.hits, self.misses)
        super().use_frames(count, policy)
        self.fault_count, self.hits, self.misses = kept


class UseFramesKeepsTheTlb(Model):
    """Leaves the old translations in the TLB."""

    def use_frames(self, count: int, policy: str) -> None:
        kept = None if self.tlb is None else list(self.tlb)
        super().use_frames(count, policy)
        self.tlb = kept


class ResidentInLoadOrder(Model):
    """Lists the resident pages in the order they were loaded."""

    def resident(self) -> list[int]:
        return sorted(self.table, key=lambda p: self.loaded_at.get(p, -1))


# ------------------------------------------------------------------ level 4 mistakes
class WalkTakesTheIndexesTheWrongWay(Model):
    """Uses the high bits of the page number to index the inner table."""

    def walk(self, address: int, entry_bytes: int) -> list[int]:
        outer, inner, offset = super().walk(address, entry_bytes)
        return [inner, outer, offset]


class EntriesPerTableFromThePageCount(Model):
    """Gives each inner table as many entries as the page has bytes."""

    def per_table(self, entry_bytes: int) -> int:
        return self.size


class TablesCountedPerPage(Model):
    """Counts a page of table for every mapped page."""

    def table_bytes(self, address_bits: int, entry_bytes: int) -> list[int]:
        linear, two = super().table_bytes(address_bits, entry_bytes)
        per = self.per_table(entry_bytes)
        tables = len({page // per for page in self.table})
        return [linear, two + (len(self.table) - tables) * self.size]


class DirectoryRoundedToAPage(Model):
    """Gives the directory a whole page when it is smaller than one."""

    def table_bytes(self, address_bits: int, entry_bytes: int) -> list[int]:
        linear, two = super().table_bytes(address_bits, entry_bytes)
        pages = self.pages_in(address_bits)
        directory = pages // self.per_table(entry_bytes) * entry_bytes
        return [linear, two - directory + max(directory, self.size)]


class LinearCountsMappedPages(Model):
    """Sizes the one-level table by the highest mapped page."""

    def table_bytes(self, address_bits: int, entry_bytes: int) -> list[int]:
        _, two = super().table_bytes(address_bits, entry_bytes)
        return [(max(self.table, default=-1) + 1) * entry_bytes, two]


class WindowOneTooLong(Model):
    """Reads one reference more than the window."""

    def window(self, window: int) -> list[int]:
        return self.history[-(window + 1) :]


class FaultsAreNotReferences(Model):
    """Leaves out of the history a translation that fails."""

    def translate(self, address: int) -> int:
        result = super().translate(address)
        if result == -1:
            self.history.pop()
        return result


class HistorySurvivesUseFrames(Model):
    """Keeps the references made before useFrames."""

    def forget_history(self) -> None:
        pass


class ThrashingWhenItJustFits(Model):
    """Calls a working set as large as memory thrashing."""

    def too_many(self, pages: int) -> bool:
        return bool(self.frames) and pages >= len(self.frames)


class ThrashingWithoutAFrameLimit(Model):
    """Compares with the number of frames even before useFrames, when there is no limit."""

    def too_many(self, pages: int) -> bool:
        return pages > len(self.frames)


class WorkingSetIsWhatIsResident(Model):
    """Reports the pages in memory as the working set."""

    def working_set(self, window: int) -> list[int]:
        if not self.frames:
            return super().working_set(window)
        return sorted(set(self.window(window)) & set(self.table))


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError):
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


def test_a_visible_case_shows_beladys_anomaly_for_fifo():
    """The same references fault more often under FIFO with four frames than with three."""
    faults = {}
    for frames in (3, 4):
        model = Model(16)
        model.use_frames(frames, "fifo")
        for page in BELADY:
            model.translate(page * 16)
        faults[frames] = model.faults()
    assert faults == {3: 9, 4: 10}
    runs = [
        [args for op, args in zip(case["ops"], case["args"], strict=True) if op == "useFrames"]
        for case in CASES
        if case.get("visible")
    ]
    assert [[3, "fifo"], [4, "fifo"]] in runs
