"""crdt-replicas promises that its hidden cases catch the classic mistakes of building replicated
data that merges without coordination: a merge that adds instead of taking the maximum, a counter
kept as one number, decrements that a maximum swallows, a register merged by arrival order or with
the tie-break the wrong way round, a remove that wins over a concurrent add, tags that are not
unique, and a delta sync that forgets a target, forwards only local changes or counts operations
instead of entries. These tests replay every case against a model of the replicas written from
the statement, which must give every expected output, and against that model with one mistake
planted at a time, which some hidden case must fail. They also check the properties the statement
promises: replicas that have seen the same updates agree whatever the merge order, and a sync
leaves the target exactly as a full merge would."""

import json
import re
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0371-crdt-replicas"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Key = tuple[str, ...]


class Model:
    """Each replica is one map from an entry key to a value that only grows, and a log of the keys
    in the order they changed. A sync sends the distinct keys logged since the target's last
    acknowledgement. Each mistake below overrides one method."""

    def __init__(self, ids: list[str]) -> None:
        self.state: dict[str, dict[Key, Any]] = {name: {} for name in ids}
        self.history: dict[str, list[Key]] = {name: [] for name in ids}
        self.acks: dict[tuple[str, str], int] = {}
        self.adds = dict.fromkeys(ids, 0)

    # --- the join of one entry
    def grows(self, key: Key, old: Any, new: Any) -> bool:
        if key[0] in ("up", "down"):
            return new > old
        if key[0] == "reg":
            return new[:2] > old[:2]
        return False

    def put(self, replica: str, key: Key, value: Any) -> None:
        entries = self.state[replica]
        if key not in entries or self.grows(key, entries[key], value):
            entries[key] = value
            self.history[replica].append(key)

    def keys(self, replica: str, kind: str, *prefix: str) -> list[Key]:
        return [
            key
            for key in self.state[replica]
            if key[0] == kind and key[1 : 1 + len(prefix)] == prefix
        ]

    # --- level 1
    def bump(self, replica: str, kind: str, counter: str, amount: int) -> int:
        key = (kind, counter, replica)
        self.put(replica, key, self.state[replica].get(key, 0) + amount)
        return self.value(replica, counter)

    def increment(self, replica: str, counter: str, amount: int) -> int:
        return self.bump(replica, "up", counter, amount)

    def decrement(self, replica: str, counter: str, amount: int) -> int:
        return self.bump(replica, "down", counter, amount)

    def value(self, replica: str, counter: str) -> int:
        entries = self.state[replica]
        ups = sum(entries[key] for key in self.keys(replica, "up", counter))
        return ups - sum(entries[key] for key in self.keys(replica, "down", counter))

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            self.put(target, key, value)

    # --- level 2
    def beats(self, new: tuple[int, str], old: tuple[int, str]) -> bool:
        return new > old

    def write(self, replica: str, register: str, text: str, timestamp: int) -> bool:
        old = self.state[replica].get(("reg", register))
        if old is not None and not self.beats((timestamp, replica), old[:2]):
            return False
        self.put(replica, ("reg", register), (timestamp, replica, text))
        return True

    def read(self, replica: str, register: str) -> str:
        return self.state[replica].get(("reg", register), (0, "", ""))[2]

    # --- level 3
    def new_tag(self, replica: str, set_name: str, element: str) -> str:
        self.adds[replica] += 1
        return f"{replica}:{self.adds[replica]}"

    def add(self, replica: str, set_name: str, element: str) -> str:
        tag = self.new_tag(replica, set_name, element)
        self.put(replica, ("tag", set_name, element, tag), True)
        return tag

    def live_tags(self, replica: str, set_name: str, element: str) -> list[Key]:
        dead = {key[3] for key in self.keys(replica, "tomb", set_name, element)}
        return [key for key in self.keys(replica, "tag", set_name, element) if key[3] not in dead]

    def remove(self, replica: str, set_name: str, element: str) -> int:
        observed = self.live_tags(replica, set_name, element)
        for key in observed:
            self.put(replica, ("tomb", *key[1:]), True)
        return len(observed)

    def contains(self, replica: str, set_name: str, element: str) -> bool:
        return bool(self.live_tags(replica, set_name, element))

    def present(self, replica: str, set_name: str) -> list[str]:
        return [key[2] for key in self.keys(replica, "tag", set_name)]

    def elements(self, replica: str, set_name: str) -> list[str]:
        found = {e for e in self.present(replica, set_name) if self.contains(replica, set_name, e)}
        return sorted(found)

    # --- level 4
    def delta(self, source: str, target: str) -> list[Key]:
        since = self.acks.get((source, target), 0)
        return list(dict.fromkeys(self.history[source][since:]))

    def sent(self, source: str, delta: list[Key]) -> int:
        return len(delta)

    def acknowledge(self, source: str, target: str) -> None:
        self.acks[(source, target)] = len(self.history[source])

    def sync(self, source: str, target: str) -> int:
        delta = self.delta(source, target)
        for key in delta:
            self.put(target, key, self.state[source][key])
        self.acknowledge(source, target)
        return self.sent(source, delta)

    def state_size(self, replica: str) -> int:
        return len(self.state[replica])


# ------------------------------------------------------------------ level 1 mistakes
class MergeAddsSlots(Model):
    """Adds the source's slots to the target's instead of taking the larger."""

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] in ("up", "down"):
                self.state[target][key] = self.state[target].get(key, 0) + value
            else:
                self.put(target, key, value)


class OneNumberPerReplica(Model):
    """Keeps one total per replica and merges by the larger total."""

    def __init__(self, ids: list[str]) -> None:
        super().__init__(ids)
        self.totals: dict[tuple[str, str], int] = {}

    def increment(self, replica: str, counter: str, amount: int) -> int:
        self.totals[(replica, counter)] = self.totals.get((replica, counter), 0) + amount
        return self.totals[(replica, counter)]

    def decrement(self, replica: str, counter: str, amount: int) -> int:
        return self.increment(replica, counter, -amount)

    def value(self, replica: str, counter: str) -> int:
        return self.totals.get((replica, counter), 0)

    def merge(self, source: str, target: str) -> None:
        for (owner, counter), total in list(self.totals.items()):
            if owner == source:
                mine = self.totals.get((target, counter), 0)
                self.totals[(target, counter)] = max(mine, total)
        super().merge(source, target)


class MergeOverwritesSlots(Model):
    """Copies every slot of the source over the target's, even an older one."""

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] in ("up", "down"):
                self.state[target][key] = value
            else:
                self.put(target, key, value)


class MergeSendsOnlyOwnSlot(Model):
    """Sends only the slots the source itself incremented."""

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] not in ("up", "down") or key[2] == source:
                self.put(target, key, value)


class DecrementInTheSameSlot(Model):
    """Subtracts from the replica's own slot, so a merge by maximum loses the decrement."""

    def decrement(self, replica: str, counter: str, amount: int) -> int:
        key = ("up", counter, replica)
        self.state[replica][key] = self.state[replica].get(key, 0) - amount
        self.history[replica].append(key)
        return self.value(replica, counter)

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] == "up":
                self.state[target][key] = max(self.state[target].get(key, 0), value)
            else:
                self.put(target, key, value)


class MergeTheOtherWay(Model):
    """Merges the target into the source."""

    def merge(self, source: str, target: str) -> None:
        super().merge(target, source)


# ------------------------------------------------------------------ level 2 mistakes
class LastMergedWins(Model):
    """Lets the incoming register win every merge."""

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] == "reg":
                self.state[target][key] = value
            else:
                self.put(target, key, value)


class TieGoesToSmallerId(Model):
    """Breaks equal timestamps by the smaller replica id."""

    def beats(self, new: tuple[int, str], old: tuple[int, str]) -> bool:
        return new[0] > old[0] or (new[0] == old[0] and new[1] < old[1])

    def grows(self, key: Key, old: Any, new: Any) -> bool:
        if key[0] == "reg":
            return self.beats(new[:2], old[:2])
        return super().grows(key, old, new)


class TieKeepsWhatIsThere(Model):
    """Keeps the target's register when the timestamps are equal."""

    def grows(self, key: Key, old: Any, new: Any) -> bool:
        if key[0] == "reg":
            return new[0] > old[0]
        return super().grows(key, old, new)


class WriteAlwaysApplies(Model):
    """Applies every local write, whatever its timestamp."""

    def write(self, replica: str, register: str, text: str, timestamp: int) -> bool:
        self.state[replica][("reg", register)] = (timestamp, replica, text)
        self.history[replica].append(("reg", register))
        return True


class EqualStampOverwrites(Model):
    """Lets a write with the same stamp replace the current value."""

    def beats(self, new: tuple[int, str], old: tuple[int, str]) -> bool:
        return new >= old

    def write(self, replica: str, register: str, text: str, timestamp: int) -> bool:
        old = self.state[replica].get(("reg", register))
        if old is not None and not self.beats((timestamp, replica), old[:2]):
            return False
        self.state[replica][("reg", register)] = (timestamp, replica, text)
        self.history[replica].append(("reg", register))
        return True


class LocalWriteComparesTimestampsOnly(Model):
    """Accepts a local write whose timestamp equals the current one, whoever wrote it."""

    def beats(self, new: tuple[int, str], old: tuple[int, str]) -> bool:
        return new[0] >= old[0] and new != old

    def write(self, replica: str, register: str, text: str, timestamp: int) -> bool:
        old = self.state[replica].get(("reg", register))
        if old is not None and not self.beats((timestamp, replica), old[:2]):
            return False
        self.state[replica][("reg", register)] = (timestamp, replica, text)
        self.history[replica].append(("reg", register))
        return True


# ------------------------------------------------------------------ level 3 mistakes
class RemoveWinsForTheElement(Model):
    """Records the removed element, so it stays removed against any add."""

    def remove(self, replica: str, set_name: str, element: str) -> int:
        observed = len(self.live_tags(replica, set_name, element))
        if observed:
            self.put(replica, ("gone", set_name, element), True)
        return observed

    def contains(self, replica: str, set_name: str, element: str) -> bool:
        if ("gone", set_name, element) in self.state[replica]:
            return False
        return super().contains(replica, set_name, element)


class TagPerReplicaAndElement(Model):
    """Reports a new tag but keys the add by replica and element, so a re-add is already removed."""

    def add(self, replica: str, set_name: str, element: str) -> str:
        tag = self.new_tag(replica, set_name, element)
        self.put(replica, ("tag", set_name, element, f"{replica}/{element}"), True)
        return tag


class MergeDropsTombstones(Model):
    """Merges the adds of a set and not the removes."""

    def merge(self, source: str, target: str) -> None:
        for key, value in list(self.state[source].items()):
            if key[0] != "tomb":
                self.put(target, key, value)


class RemoveReportsOne(Model):
    """Returns 1 for a present element, however many tags it removed."""

    def remove(self, replica: str, set_name: str, element: str) -> int:
        return min(super().remove(replica, set_name, element), 1)


class ElementsInAddOrder(Model):
    """Lists the elements in the order they were first added."""

    def elements(self, replica: str, set_name: str) -> list[str]:
        live = self.present(replica, set_name)
        return list(dict.fromkeys(e for e in live if self.contains(replica, set_name, e)))


class ElementsOncePerTag(Model):
    """Lists an element once for each live tag."""

    def elements(self, replica: str, set_name: str) -> list[str]:
        return sorted(
            key[2]
            for key in self.keys(replica, "tag", set_name)
            if key in self.live_tags(replica, set_name, key[2])
        )


class TagCountPerSet(Model):
    """Numbers the adds of each set separately."""

    def new_tag(self, replica: str, set_name: str, element: str) -> str:
        count = 1 + sum(
            1 for key in self.keys(replica, "tag", set_name) if key[3].startswith(f"{replica}:")
        )
        return f"{replica}:{count}"


class TagCountFromAllTags(Model):
    """Numbers an add after every tag the replica holds, including merged ones."""

    def new_tag(self, replica: str, set_name: str, element: str) -> str:
        return f"{replica}:{1 + len(self.keys(replica, 'tag'))}"


class ContainsIgnoresTombstones(Model):
    """Answers whether the element was ever added."""

    def contains(self, replica: str, set_name: str, element: str) -> bool:
        return bool(self.keys(replica, "tag", set_name, element))


# ------------------------------------------------------------------ level 4 mistakes
class OneAckPerSource(Model):
    """Remembers one acknowledgement per source, whatever the target."""

    def delta(self, source: str, target: str) -> list[Key]:
        return super().delta(source, "*")

    def acknowledge(self, source: str, target: str) -> None:
        super().acknowledge(source, "*")


class SendsOnlyLocalChanges(Model):
    """Sends only what the source changed itself, not what it received."""

    def __init__(self, ids: list[str]) -> None:
        super().__init__(ids)
        self.local: dict[str, set[Key]] = {name: set() for name in ids}
        self.receiving = False

    def put(self, replica: str, key: Key, value: Any) -> None:
        if not self.receiving:
            self.local[replica].add(key)
        super().put(replica, key, value)

    def merge(self, source: str, target: str) -> None:
        self.receiving = True
        super().merge(source, target)
        self.receiving = False

    def delta(self, source: str, target: str) -> list[Key]:
        return [key for key in super().delta(source, target) if key in self.local[source]]

    def sync(self, source: str, target: str) -> int:
        delta = self.delta(source, target)
        self.receiving = True
        for key in delta:
            self.put(target, key, self.state[source][key])
        self.receiving = False
        self.acknowledge(source, target)
        return len(delta)


class CountsChangesNotEntries(Model):
    """Counts every change since the acknowledgement, so one entry changed twice counts twice."""

    def sync(self, source: str, target: str) -> int:
        changes = len(self.history[source]) - self.acks.get((source, target), 0)
        super().sync(source, target)
        return changes


class SyncCountsTheFullState(Model):
    """Applies the delta but reports the size of the whole state."""

    def sent(self, source: str, delta: list[Key]) -> int:
        return len(self.state[source])


class SyncSkipsWhatCameFromTheTarget(Model):
    """Never sends back an entry whose last change came from the target."""

    def __init__(self, ids: list[str]) -> None:
        super().__init__(ids)
        self.origin: dict[tuple[str, Key], str] = {}
        self.sender = ""

    def put(self, replica: str, key: Key, value: Any) -> None:
        before = len(self.history[replica])
        super().put(replica, key, value)
        if len(self.history[replica]) > before:
            self.origin[(replica, key)] = self.sender

    def merge(self, source: str, target: str) -> None:
        self.sender = source
        super().merge(source, target)
        self.sender = ""

    def delta(self, source: str, target: str) -> list[Key]:
        return [k for k in super().delta(source, target) if self.origin.get((source, k)) != target]

    def sync(self, source: str, target: str) -> int:
        self.sender = source
        sent = super().sync(source, target)
        self.sender = ""
        return sent


class SizeCountsSlotsOnce(Model):
    """Counts a counter slot as one entry even when it has gone up and down."""

    def state_size(self, replica: str) -> int:
        slots = {key[1:] for key in self.state[replica] if key[0] in ("up", "down")}
        others = [key for key in self.state[replica] if key[0] not in ("up", "down")]
        return len(slots) + len(others)


class SizeCountsRemovedTagsOnce(Model):
    """Counts a removed tag as one entry."""

    def state_size(self, replica: str) -> int:
        return len([key for key in self.state[replica] if key[0] != "tomb"])


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def run(model_type: type[Model], case: Mapping[str, Any]) -> tuple[Model, list[Any]]:
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return model, [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return run(model_type, case)[1] == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert run(Model, case)[1] == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_replicas_that_have_seen_everything_agree_whatever_the_merge_order(case):
    """After each case, gossip every state around a ring in one order and in the reverse order:
    every replica ends with the same entries both times."""
    finals = []
    ids = case["args"][0][0]
    for ring in (list(ids), list(reversed(ids))):
        model, _ = run(Model, case)
        for _ in range(2):
            for source, target in pairwise([*ring, ring[0]]):
                model.merge(source, target)
        states = [model.state[name] for name in ring]
        assert all(state == states[0] for state in states)
        finals.append(states[0])
    assert finals[0] == finals[1]


@pytest.mark.parametrize("case", [c for c in CASES if "sync" in c["ops"]], ids=lambda c: c["id"])
def test_a_sync_leaves_the_target_as_a_full_merge_would(case):
    """Replays the case twice, once as written and once with every sync replaced by a merge, and
    compares the states of every replica after every operation."""
    by_sync = Model(*case["args"][0])
    by_merge = Model(*case["args"][0])
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        getattr(by_sync, snake_case(op))(*arguments)
        getattr(by_merge, "merge" if op == "sync" else snake_case(op))(*arguments)
        assert by_sync.state == by_merge.state, (op, arguments)


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_a_sync_sends_fewer_entries_than_the_full_state_somewhere():
    saving = []
    for case in CASES:
        model = Model(*case["args"][0])
        for op, arguments, got in zip(
            case["ops"][1:], case["args"][1:], case["expected"][1:], strict=True
        ):
            if op == "sync":
                saving.append(got < model.state_size(arguments[0]))
            getattr(model, snake_case(op))(*arguments)
    assert any(saving)
