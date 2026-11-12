"""logical-clocks promises that its hidden cases catch the classic mistakes with logical clocks: a
receive that does not jump past both clocks, ties broken by name or by the process number as
text, refused calls that still tick, a comparison read from Lamport timestamps, a vector merge that
loses what the receiver knew, siblings chosen by the latest write or across the whole history,
and every wrong branch of the hybrid clock's receive rule. These tests replay every case against
a model written from the statement's definitions (happened-before as reachability, a vector as the
count of each process's events in the causal past), which must give every expected output, and
against that model with one mistake planted at a time, which some hidden case must fail."""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0369-logical-clocks"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


@dataclass
class Event:
    name: str
    process: int
    kind: str
    wall: int
    message: str = ""
    key: str = ""
    value: str = ""


class Model:
    """The history as a list of events in call order. Lamport and hybrid stamps come from
    replaying the rules over that list; causality comes from walking it backwards."""

    def __init__(self, processes: int) -> None:
        self.processes = processes
        self.history: list[Event] = []

    # --- recording
    def refused(self, process: int, name: str) -> bool:
        return not 0 <= process < self.processes or any(e.name == name for e in self.history)

    def message_refused(self, process: int, message: str) -> bool:
        sends = [e for e in self.history if e.name == message and e.kind == "send"]
        taken = any(e.kind == "receive" and e.message == message for e in self.history)
        return not sends or taken or sends[0].process == process

    def add(self, event: Event) -> int:
        if self.refused(event.process, event.name):
            return -1
        if event.kind == "receive" and self.message_refused(event.process, event.message):
            return -1
        self.history.append(event)
        return self.lamport_stamps()[event.name]

    def local(self, process: int, event: str, wall: int) -> int:
        return self.add(Event(event, process, "local", wall))

    def send(self, process: int, event: str, wall: int) -> int:
        return self.add(Event(event, process, "send", wall))

    def receive(self, process: int, event: str, message: str, wall: int) -> int:
        return self.add(Event(event, process, "receive", wall, message))

    def write(self, process: int, event: str, key: str, value: str, wall: int) -> int:
        return self.add(Event(event, process, "write", wall, key=key, value=value))

    # --- level 1
    def lamport_receive(self, own: int, stamp: int) -> int:
        return max(own, stamp) + 1

    def lamport_stamps(self) -> dict[str, int]:
        clock = [0] * self.processes
        stamps: dict[str, int] = {}
        for e in self.history:
            if e.kind == "receive":
                clock[e.process] = self.lamport_receive(clock[e.process], stamps[e.message])
            else:
                clock[e.process] += 1
            stamps[e.name] = clock[e.process]
        return stamps

    def order(self, keys: dict[str, tuple[int, ...]]) -> list[str]:
        return sorted(keys, key=lambda name: keys[name])

    def total_order(self) -> list[str]:
        stamps = self.lamport_stamps()
        return self.order({e.name: (stamps[e.name], e.process) for e in self.history})

    # --- level 2
    def past(self, name: str) -> set[str]:
        """The event and every event that happened before it."""
        index = next(i for i, e in enumerate(self.history) if e.name == name)
        seen: set[str] = set()
        stack = [index]
        while stack:
            at = stack.pop()
            e = self.history[at]
            if e.name in seen:
                continue
            seen.add(e.name)
            earlier = [i for i in range(at) if self.history[i].process == e.process]
            if earlier:
                stack.append(earlier[-1])
            if e.kind == "receive":
                stack.append(next(i for i, s in enumerate(self.history) if s.name == e.message))
        return seen

    def known(self, name: str) -> bool:
        return any(e.name == name for e in self.history)

    def before(self, first: str, second: str) -> bool:
        return first != second and first in self.past(second)

    def vector(self, event: str) -> list[int]:
        if not self.known(event):
            return []
        past = self.past(event)
        return [
            sum(e.process == j and e.name in past for e in self.history)
            for j in range(self.processes)
        ]

    def compare(self, first: str, second: str) -> str:
        if not self.known(first) or not self.known(second):
            return ""
        if first == second:
            return "same"
        if self.before(first, second):
            return "before"
        if self.before(second, first):
            return "after"
        return "concurrent"

    # --- level 3
    def latest_past(self, process: int) -> set[str]:
        mine = [e.name for e in self.history if e.process == process]
        return self.past(mine[-1]) if mine else set()

    def writes_known(self, process: int, key: str) -> list[Event]:
        past = self.latest_past(process)
        return [e for e in self.history if e.kind == "write" and e.key == key and e.name in past]

    def siblings(self, process: int, key: str) -> list[Event]:
        known = self.writes_known(process, key)
        return [w for w in known if not any(self.before(w.name, o.name) for o in known)]

    def values(self, siblings: list[Event]) -> list[str]:
        return sorted(w.value for w in siblings)

    def read(self, process: int, key: str) -> list[str]:
        if not 0 <= process < self.processes:
            return []
        return self.values(self.siblings(process, key))

    def concurrent_writes(self, key: str) -> list[list[str]]:
        names = sorted(e.name for e in self.history if e.kind == "write" and e.key == key)
        return [
            [a, b]
            for i, a in enumerate(names)
            for b in names[i + 1 :]
            if self.compare(a, b) == "concurrent"
        ]

    # --- level 4
    def local_hybrid(self, logical: int, count: int, pt: int) -> tuple[int, int]:
        new = max(logical, pt)
        return (new, count + 1 if new == logical else 0)

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        (logical, count), (sent_logical, sent_count) = own, sent
        new = max(logical, sent_logical, pt)
        if new == logical == sent_logical:
            return (new, max(count, sent_count) + 1)
        if new == logical:
            return (new, count + 1)
        if new == sent_logical:
            return (new, sent_count + 1)
        return (new, 0)

    def start_hybrid(self) -> tuple[int, int]:
        return (0, 0)

    def hybrid_stamps(self) -> dict[str, tuple[int, int]]:
        clock = [self.start_hybrid()] * self.processes
        stamps: dict[str, tuple[int, int]] = {}
        for e in self.history:
            if e.kind == "receive":
                clock[e.process] = self.receive_hybrid(clock[e.process], stamps[e.message], e.wall)
            else:
                clock[e.process] = self.local_hybrid(*clock[e.process], e.wall)
            stamps[e.name] = clock[e.process]
        return stamps

    def hlc(self, event: str) -> list[int]:
        stamps = self.hybrid_stamps()
        return list(stamps[event]) if event in stamps else []

    def hlc_order(self) -> list[str]:
        stamps = self.hybrid_stamps()
        return self.order({e.name: (*stamps[e.name], e.process) for e in self.history})

    def offset(self, logical: int, wall: int) -> int:
        return logical - wall

    def max_offset(self) -> int:
        stamps = self.hybrid_stamps()
        return max((self.offset(stamps[e.name][0], e.wall) for e in self.history), default=0)


# ------------------------------------------------------------------ level 1 mistakes
class ReceiveTakesTheMessagePlusOne(Model):
    """Forgets the receiver's own clock on a receive."""

    def lamport_receive(self, own: int, stamp: int) -> int:
        return stamp + 1


class ReceiveTicksOnlyItsOwnClock(Model):
    """Treats a receive like a local event."""

    def lamport_receive(self, own: int, stamp: int) -> int:
        return own + 1


class ReceiveWithoutTheTick(Model):
    """Takes the larger clock and does not add one."""

    def lamport_receive(self, own: int, stamp: int) -> int:
        return max(own, stamp)


class TiesByName(Model):
    """Breaks equal timestamps by event name."""

    def total_order(self) -> list[str]:
        stamps = self.lamport_stamps()
        return sorted(stamps, key=lambda name: (stamps[name], name))


class TiesByProcessAsText(Model):
    """Compares process numbers as text, so 10 comes before 2."""

    def order(self, keys: dict[str, tuple[int, ...]]) -> list[str]:
        return sorted(keys, key=lambda name: (keys[name][:-1], str(keys[name][-1])))


class TiesByCallOrder(Model):
    """Sorts by timestamp only, keeping the order of the calls on a tie."""

    def total_order(self) -> list[str]:
        stamps = self.lamport_stamps()
        return sorted(stamps, key=lambda name: stamps[name])


class OrderByWallClock(Model):
    """Trusts the physical readings."""

    def total_order(self) -> list[str]:
        return [e.name for e in sorted(self.history, key=lambda e: (e.wall, e.process))]


class RefusedReceiveStillTicks(Model):
    """Advances the receiver's clock before checking the message."""

    def receive(self, process: int, event: str, message: str, wall: int) -> int:
        answer = super().receive(process, event, message, wall)
        if answer == -1 and 0 <= process < self.processes:
            self.history.append(Event(f"#tick{len(self.history)}", process, "local", wall))
        return answer

    def total_order(self) -> list[str]:
        return [name for name in super().total_order() if not name.startswith("#")]


class FailedReceiveUsesUpTheMessage(Model):
    """Marks the message as received even when the receive is refused for its own name."""

    def receive(self, process: int, event: str, message: str, wall: int) -> int:
        answer = super().receive(process, event, message, wall)
        if answer == -1 and not self.message_refused(process, message):
            self.history.append(Event(f"#gone{len(self.history)}", -1, "receive", 0, message))
        return answer

    def lamport_stamps(self) -> dict[str, int]:
        real = [e for e in self.history if e.process >= 0]
        hidden, self.history = self.history, real
        try:
            return super().lamport_stamps()
        finally:
            self.history = hidden

    def total_order(self) -> list[str]:
        stamps = self.lamport_stamps()
        events = [e for e in self.history if e.process >= 0]
        return self.order({e.name: (stamps[e.name], e.process) for e in events})


class SenderMayReceive(Model):
    """Lets a process receive its own message."""

    def message_refused(self, process: int, message: str) -> bool:
        return super().message_refused(process + self.processes, message)


class MessageMayArriveTwice(Model):
    """Accepts a second receive of the same message."""

    def message_refused(self, process: int, message: str) -> bool:
        sends = [e for e in self.history if e.name == message and e.kind == "send"]
        return not sends or sends[0].process == process


class AnyEventIsAMessage(Model):
    """Accepts a local event as the message of a receive."""

    def message_refused(self, process: int, message: str) -> bool:
        found = [e for e in self.history if e.name == message]
        taken = any(e.kind == "receive" and e.message == message for e in self.history)
        return not found or taken or found[0].process == process


# ------------------------------------------------------------------ level 2 mistakes
class CompareByLamport(Model):
    """Reads before and after from Lamport timestamps."""

    def compare(self, first: str, second: str) -> str:
        answer = super().compare(first, second)
        if answer in ("", "same"):
            return answer
        stamps = self.lamport_stamps()
        if stamps[first] == stamps[second]:
            return "concurrent"
        return "before" if stamps[first] < stamps[second] else "after"


class ReplayedVectors(Model):
    """Vectors from replaying an update rule; each mistake below changes the rule."""

    def merge(self, mine: list[int], theirs: list[int]) -> list[int]:
        return [max(a, b) for a, b in zip(mine, theirs, strict=True)]

    def tick_on_receive(self) -> int:
        return 1

    def replay(self) -> dict[str, list[int]]:
        clock = [[0] * self.processes for _ in range(self.processes)]
        stamps: dict[str, list[int]] = {}
        for e in self.history:
            mine = list(clock[e.process])
            if e.kind == "receive":
                mine = self.merge(mine, stamps[e.message])
                mine[e.process] += self.tick_on_receive()
            else:
                mine[e.process] += 1
            clock[e.process] = mine
            stamps[e.name] = mine
        return stamps

    def vector(self, event: str) -> list[int]:
        return list(self.replay().get(event, []))

    def before(self, first: str, second: str) -> bool:
        stamps = self.replay()
        one, other = stamps[first], stamps[second]
        return one != other and all(a <= b for a, b in zip(one, other, strict=True))


class MergeTakesTheMessage(ReplayedVectors):
    """Replaces the receiver's vector by the message's."""

    def merge(self, mine: list[int], theirs: list[int]) -> list[int]:
        return list(theirs)


class MergeWithoutTheTick(ReplayedVectors):
    """Merges on a receive but does not count the receive itself."""

    def tick_on_receive(self) -> int:
        return 0


class SameBeforeUnknown(Model):
    """Answers same for a name compared with itself, known or not."""

    def compare(self, first: str, second: str) -> str:
        return "same" if first == second else super().compare(first, second)


# ------------------------------------------------------------------ level 3 mistakes
class LatestWallWins(Model):
    """Keeps only the known write with the latest physical reading."""

    def siblings(self, process: int, key: str) -> list[Event]:
        known = self.writes_known(process, key)
        return [max(known, key=lambda w: w.wall)] if known else []


class LatestLamportWins(Model):
    """Keeps only the known write with the largest Lamport timestamp."""

    def siblings(self, process: int, key: str) -> list[Event]:
        stamps = self.lamport_stamps()
        known = self.writes_known(process, key)
        return [max(known, key=lambda w: (stamps[w.name], w.process))] if known else []


class SiblingsAcrossTheWholeHistory(Model):
    """Ignores what the process knows of."""

    def writes_known(self, process: int, key: str) -> list[Event]:
        return [e for e in self.history if e.kind == "write" and e.key == key]


class SiblingValuesDeduplicated(Model):
    """Returns each value once."""

    def values(self, siblings: list[Event]) -> list[str]:
        return sorted({w.value for w in siblings})


class SiblingsByEventName(Model):
    """Lists the values in the order of the events' names."""

    def values(self, siblings: list[Event]) -> list[str]:
        return [w.value for w in sorted(siblings, key=lambda w: w.name)]


class NewWriteDropsEveryVersion(Model):
    """A new write replaces every earlier write of the key, seen or not."""

    def writes_known(self, process: int, key: str) -> list[Event]:
        known = super().writes_known(process, key)
        writes = [e for e in self.history if e.kind == "write" and e.key == key]
        superseded = {w.name for i, w in enumerate(writes) if i < len(writes) - 1}
        return [w for w in known if w.name not in superseded or w is writes[-1]]


class KeysShareSiblings(Model):
    """Compares the writes of every key with each other."""

    def writes_known(self, process: int, key: str) -> list[Event]:
        past = self.latest_past(process)
        return [e for e in self.history if e.kind == "write" and e.name in past]


class PairsInCallOrder(Model):
    """Lists concurrent pairs in the order the writes were made."""

    def concurrent_writes(self, key: str) -> list[list[str]]:
        names = [e.name for e in self.history if e.kind == "write" and e.key == key]
        return [
            [a, b]
            for i, a in enumerate(names)
            for b in names[i + 1 :]
            if self.compare(a, b) == "concurrent"
        ]


# ------------------------------------------------------------------ level 4 mistakes
class CounterNeverResets(Model):
    """Counts up even when the physical reading moves l forward."""

    def local_hybrid(self, logical: int, count: int, pt: int) -> tuple[int, int]:
        return (max(logical, pt), count + 1)


class BothEqualCountsOwnOnly(Model):
    """Ignores the message's counter when all three agree."""

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        new = max(own[0], sent[0], pt)
        if new == own[0] == sent[0]:
            return (new, own[1] + 1)
        return super().receive_hybrid(own, sent, pt)


class OwnAheadCountsTheMessage(Model):
    """Continues the message's counter when the receiver's l wins."""

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        new = max(own[0], sent[0], pt)
        if new == own[0] != sent[0]:
            return (new, sent[1] + 1)
        return super().receive_hybrid(own, sent, pt)


class MessageAheadCountsOwn(Model):
    """Continues the receiver's counter when the message's l wins."""

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        new = max(own[0], sent[0], pt)
        if new == sent[0] != own[0]:
            return (new, own[1] + 1)
        return super().receive_hybrid(own, sent, pt)


class PhysicalAheadKeepsCounting(Model):
    """Does not reset the counter when the reading is ahead of both."""

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        new = max(own[0], sent[0], pt)
        if new not in (own[0], sent[0]):
            return (new, max(own[1], sent[1]) + 1)
        return super().receive_hybrid(own, sent, pt)


class ReceiveLikeALocalEvent(Model):
    """Ignores the stamp the message carries."""

    def receive_hybrid(
        self, own: tuple[int, int], sent: tuple[int, int], pt: int
    ) -> tuple[int, int]:
        return self.local_hybrid(*own, pt)


class FirstEventCountsFromZero(Model):
    """Starts the counter so that the first event gets c = 0."""

    def start_hybrid(self) -> tuple[int, int]:
        return (0, -1)


class LFollowsTheReading(Model):
    """Sets l to the physical reading, so it goes back when the clock does."""

    def local_hybrid(self, logical: int, count: int, pt: int) -> tuple[int, int]:
        return (pt, count + 1 if pt == logical else 0)


class OffsetTheWrongWayRound(Model):
    """Measures how far the reading is ahead of l."""

    def offset(self, logical: int, wall: int) -> int:
        return wall - logical


class HybridOrderWithoutCounter(Model):
    """Orders by l and process only."""

    def hlc_order(self) -> list[str]:
        stamps = self.hybrid_stamps()
        return self.order({e.name: (stamps[e.name][0], e.process) for e in self.history})


class HybridTiesByName(Model):
    """Breaks equal pairs by event name."""

    def hlc_order(self) -> list[str]:
        stamps = self.hybrid_stamps()
        return sorted(stamps, key=lambda name: (stamps[name], name))


MISTAKES: Sequence[type[Model]] = [
    cls
    for cls in (*Model.__subclasses__(), *ReplayedVectors.__subclasses__())
    if cls is not ReplayedVectors
]


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, StopIteration):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


def test_the_replayed_vectors_agree_with_the_definition():
    for case in CASES:
        assert outputs(ReplayedVectors, case) == case["expected"], case["id"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_take_every_branch_of_the_hybrid_receive_rule():
    taken: set[str] = set()

    class Recording(Model):
        def receive_hybrid(
            self, own: tuple[int, int], sent: tuple[int, int], pt: int
        ) -> tuple[int, int]:
            new = max(own[0], sent[0], pt)
            if new == own[0] == sent[0]:
                taken.add("both")
            elif new == own[0]:
                taken.add("own")
            elif new == sent[0]:
                taken.add("message")
            else:
                taken.add("physical")
            return super().receive_hybrid(own, sent, pt)

    for case in HIDDEN_CASES:
        if case["level"] == 4:
            outputs(Recording, case)
    assert taken == {"both", "own", "message", "physical"}
