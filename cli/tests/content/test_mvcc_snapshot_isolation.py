"""mvcc-snapshot-isolation promises that its hidden cases catch the classic mistakes of a
multiversion store: a clock that skips the snapshots, reads that see later or uncommitted writes,
a lost update let through, commits and aborts that tick or leave versions, serializable checks that
include plain transactions, forget reads at the commit, miss one kind of antidependency, keep the
edges of aborted transactions or never abort early, and a vacuum with the wrong horizon or the
wrong report. These tests replay every case against a model of the store written from the
statement, a flat history of versions and a set of edges where the reference keeps lists per key,
which must give every expected output, and against that model with one mistake planted at a time,
which some hidden case must fail. A mistake that crashes fails its case, as a thrown exception does
in the grader."""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0368-mvcc-snapshot-isolation"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Version = tuple[str, float, str, int]
"""key, stamp, value, writer (0 for a put)"""


class Tx:
    def __init__(self, start: float, serializable: bool) -> None:
        self.start = start
        self.serializable = serializable
        self.state = "active"
        self.commit_time = 0
        self.writes: dict[str, str] = {}
        self.reads: set[str] = set()


class Model:
    """The store as the statement words it, one rule per method. Each mistake below overrides one
    rule."""

    def __init__(self) -> None:
        self.clock = 0
        self.history: list[Version] = []
        self.txs: dict[int, Tx] = {}
        self.edges: set[tuple[int, int]] = set()

    def tick(self) -> int:
        self.clock += 1
        return self.clock

    # --- level 1
    def put(self, key: str, value: str) -> int:
        stamp = self.tick()
        self.history.append((key, stamp, value, 0))
        return stamp

    def begin(self) -> int:
        return self.open(serializable=False)

    def open(self, serializable: bool) -> int:
        tx = self.tick()
        self.txs[tx] = Tx(tx, serializable)
        return tx

    def active(self, tx: int) -> Tx | None:
        t = self.txs.get(tx)
        return t if t is not None and t.state == "active" else None

    def visible(self, t: Tx, key: str) -> str:
        seen = [
            (stamp, value) for k, stamp, value, _ in self.history if k == key and stamp < t.start
        ]
        return max(seen)[1] if seen else ""

    def read(self, tx: int, key: str) -> str:
        t = self.active(tx)
        if t is None:
            return self.unknown_read(key)
        if key in t.writes and self.reads_own_writes():
            return t.writes[key]
        if self.takes_part(t) and not self.note_read(tx, key):
            return ""
        return self.visible(t, key)

    def unknown_read(self, key: str) -> str:
        return ""

    def reads_own_writes(self) -> bool:
        return True

    def versions(self, key: str) -> list[str]:
        mine = sorted((stamp, value) for k, stamp, value, _ in self.history if k == key)
        return [f"{stamp}:{value}" for stamp, value in reversed(mine)]

    # --- level 2
    def write(self, tx: int, key: str, value: str) -> bool:
        t = self.active(tx)
        if t is None:
            return False
        if self.takes_part(t) and not self.note_write(tx, key):
            return False
        t.writes[key] = value
        return True

    def commit(self, tx: int) -> str:
        t = self.active(tx)
        if t is None:
            return "not-active"
        for check in self.commit_checks():
            refusal = check(tx, t)
            if refusal:
                self.refuse(t)
                return refusal
        stamp = self.tick()
        t.state, t.commit_time = "committed", stamp
        for key, value in t.writes.items():
            self.history.append((key, stamp, value, tx))
        return "committed"

    def refuse(self, t: Tx) -> None:
        t.state = "aborted"

    def commit_checks(self) -> list[Callable[[int, Tx], str | None]]:
        return [self.write_conflict, self.pivot]

    def write_conflict(self, tx: int, t: Tx) -> str | None:
        changed = any(k in t.writes and stamp > t.start for k, stamp, _, _ in self.history)
        return "write-conflict" if changed else None

    def abort(self, tx: int) -> bool:
        t = self.active(tx)
        if t is None:
            return False
        t.state = "aborted"
        return True

    def status(self, tx: int) -> str:
        t = self.txs.get(tx)
        return t.state if t is not None else "unknown"

    # --- level 3
    def begin_serializable(self) -> int:
        return self.open(serializable=True)

    def takes_part(self, t: Tx) -> bool:
        return t.serializable

    def serial(self, tx: int) -> bool:
        t = self.txs.get(tx)
        return t is not None and self.takes_part(t) and t.state != "aborted"

    def live(self, edge: tuple[int, int]) -> bool:
        return all(self.txs[end].state != "aborted" for end in edge)

    def live_in(self, tx: int) -> set[int]:
        return {r for r, w in self.edges if w == tx and self.live((r, w))}

    def live_out(self, tx: int) -> set[int]:
        return {w for r, w in self.edges if r == tx and self.live((r, w))}

    def missed_writers(self, tx: int, key: str) -> tuple[set[int], set[int]]:
        t = self.txs[tx]
        committed = {
            w for k, stamp, _, w in self.history if k == key and stamp > t.start and self.serial(w)
        }
        buffered = {
            other
            for other, u in self.txs.items()
            if other != tx and self.serial(other) and u.state == "active" and key in u.writes
        }
        return committed, buffered

    def note_read(self, tx: int, key: str) -> bool:
        committed, buffered = self.missed_writers(tx, key)
        if self.aborts_reader(committed):
            self.txs[tx].state = "aborted"
            return False
        self.txs[tx].reads.add(key)
        for writer in committed | buffered:
            self.edges.add((tx, writer))
        return True

    def aborts_reader(self, committed: set[int]) -> bool:
        return any(self.txs[w].state == "committed" and self.live_out(w) for w in committed)

    def overlaps(self, reader: Tx, writer: Tx) -> bool:
        return reader.state == "active" or reader.commit_time > writer.start

    def readers_of(self, tx: int, key: str) -> set[int]:
        t = self.txs[tx]
        return {
            other
            for other, u in self.txs.items()
            if other != tx and self.serial(other) and key in u.reads and self.overlaps(u, t)
        }

    def note_write(self, tx: int, key: str) -> bool:
        readers = self.readers_of(tx, key)
        if self.aborts_writer(readers):
            self.txs[tx].state = "aborted"
            return False
        for reader in readers:
            self.edges.add((reader, tx))
        return True

    def aborts_writer(self, readers: set[int]) -> bool:
        return any(self.txs[r].state == "committed" and self.live_in(r) for r in readers)

    def pivot(self, tx: int, t: Tx) -> str | None:
        if self.takes_part(t) and self.live_in(tx) and self.live_out(tx):
            return "dangerous-structure"
        return None

    def antidependencies(self, tx: int) -> list[str]:
        t = self.txs.get(tx)
        if t is None or t.state == "aborted":
            return []
        return self.format_edges(sorted(self.live_in(tx)), sorted(self.live_out(tx)))

    def format_edges(self, ins: list[int], outs: list[int]) -> list[str]:
        return [f"in:{r}" for r in ins] + [f"out:{w}" for w in outs]

    # --- level 4
    def horizon(self) -> int:
        starts = [t.start for t in self.txs.values() if t.state == "active"]
        return int(min(starts)) if starts else self.clock

    def dead(self, version: Version, limit: int) -> bool:
        key, stamp = version[0], version[1]
        return any(k == key and stamp < s <= limit for k, s, _, _ in self.history)

    def vacuum(self) -> list[str]:
        limit = self.horizon()
        gone = [v for v in self.history if self.dead(v, limit)]
        self.history = [v for v in self.history if v not in gone]
        return self.report([(key, int(stamp)) for key, stamp, _, _ in gone])

    def report(self, gone: list[tuple[str, int]]) -> list[str]:
        return [f"{key}@{stamp}" for key, stamp in sorted(gone)]


class BeginDoesNotTick(Model):
    """Numbers transactions apart from the clock and starts them at the last commit."""

    def open(self, serializable: bool) -> int:
        tx = 1000 + len(self.txs)
        self.txs[tx] = Tx(self.clock + 0.5, serializable)
        return tx


class SnapshotSeesLaterCommits(Model):
    """Reads the newest committed version, whenever it was committed."""

    def visible(self, t: Tx, key: str) -> str:
        seen = [(stamp, value) for k, stamp, value, _ in self.history if k == key]
        return max(seen)[1] if seen else ""


class VersionsOldestFirst(Model):
    """Lists the versions oldest first."""

    def versions(self, key: str) -> list[str]:
        return list(reversed(super().versions(key)))


class UnknownTransactionReadsTheLatest(Model):
    """Answers a read with an unknown id from the newest version."""

    def unknown_read(self, key: str) -> str:
        mine = sorted((stamp, value) for k, stamp, value, _ in self.history if k == key)
        return mine[-1][1] if mine else ""


class NoReadYourWrites(Model):
    """Reads the snapshot even for a key the transaction wrote."""

    def reads_own_writes(self) -> bool:
        return False


class SeesUncommittedWrites(Model):
    """Lets a read see the latest buffered write of any active transaction."""

    def visible(self, t: Tx, key: str) -> str:
        pending = [
            u.writes[key] for u in self.txs.values() if u.state == "active" and key in u.writes
        ]
        return pending[-1] if pending else super().visible(t, key)


class LastCommitterWins(Model):
    """Never refuses a commit for a write conflict."""

    def write_conflict(self, tx: int, t: Tx) -> str | None:
        return None


class PutsDoNotConflict(Model):
    """Counts only the versions of transactions as conflicts, not those of a put."""

    def write_conflict(self, tx: int, t: Tx) -> str | None:
        changed = any(
            k in t.writes and stamp > t.start and writer != 0
            for k, stamp, _, writer in self.history
        )
        return "write-conflict" if changed else None


class ConflictOnReadKeysToo(Model):
    """Also refuses a commit when a key it only read has changed."""

    def write_conflict(self, tx: int, t: Tx) -> str | None:
        seen = set(t.writes) | t.reads
        changed = any(k in seen and stamp > t.start for k, stamp, _, _ in self.history)
        return "write-conflict" if changed else super().write_conflict(tx, t)


class RefusedCommitTicks(Model):
    """Ticks the clock for a refused commit."""

    def refuse(self, t: Tx) -> None:
        super().refuse(t)
        self.tick()


class AbortTicks(Model):
    """Ticks the clock for an abort."""

    def abort(self, tx: int) -> bool:
        done = super().abort(tx)
        if done:
            self.tick()
        return done


class ReadOnlyCommitDoesNotTick(Model):
    """Commits a transaction that wrote nothing without a tick."""

    def commit(self, tx: int) -> str:
        t = self.active(tx)
        if t is not None and not t.writes and not self.pivot(tx, t):
            t.state, t.commit_time = "committed", self.clock
            return "committed"
        return super().commit(tx)


class CommitKeepsTheFirstValue(Model):
    """Stores the first value written to a key instead of the last."""

    def write(self, tx: int, key: str, value: str) -> bool:
        t = self.active(tx)
        if t is not None and key in t.writes:
            return True
        return super().write(tx, key, value)


class PlainTransactionsTakePart(Model):
    """Records reads and edges for every transaction, checking only serializable ones at commit."""

    def takes_part(self, t: Tx) -> bool:
        return True

    def pivot(self, tx: int, t: Tx) -> str | None:
        return super().pivot(tx, t) if t.serializable else None


class EdgesOutliveAborts(Model):
    """Keeps counting an edge after one of its transactions aborted, as two flags would."""

    def live(self, edge: tuple[int, int]) -> bool:
        return True

    def antidependencies(self, tx: int) -> list[str]:
        t = self.txs.get(tx)
        if t is None or t.state == "aborted":
            return []
        return super().antidependencies(tx)


class ReadsForgottenAtCommit(Model):
    """Drops a transaction's reads when it commits."""

    def commit(self, tx: int) -> str:
        status = super().commit(tx)
        if status == "committed":
            self.txs[tx].reads.clear()
        return status


class NoEdgeToBufferedWrites(Model):
    """Only notices the committed versions a read missed."""

    def missed_writers(self, tx: int, key: str) -> tuple[set[int], set[int]]:
        committed, _ = super().missed_writers(tx, key)
        return committed, set()


class NoEdgeAtWrites(Model):
    """Notices antidependencies at reads only."""

    def readers_of(self, tx: int, key: str) -> set[int]:
        return set()


class EdgesFromEarlierReaders(Model):
    """Adds an edge from a reader that committed before the writer began."""

    def overlaps(self, reader: Tx, writer: Tx) -> bool:
        return True


class OwnWritesCountAsReads(Model):
    """Records a read of a key the transaction wrote itself."""

    def read(self, tx: int, key: str) -> str:
        t = self.active(tx)
        own = t is not None and key in t.writes and self.takes_part(t)
        if own and not self.note_read(tx, key):
            return ""
        return super().read(tx, key)


class NoEarlyAborts(Model):
    """Never aborts at a read or a write; only the pivot's own commit is checked."""

    def aborts_reader(self, committed: set[int]) -> bool:
        return False

    def aborts_writer(self, readers: set[int]) -> bool:
        return False


class PivotCheckedFirst(Model):
    """Checks for a dangerous structure before the write conflict."""

    def commit_checks(self) -> list[Callable[[int, Tx], str | None]]:
        return [self.pivot, self.write_conflict]


class AnyEdgeIsDangerous(Model):
    """Refuses a serializable commit with an edge in or an edge out."""

    def pivot(self, tx: int, t: Tx) -> str | None:
        if self.takes_part(t) and (self.live_in(tx) or self.live_out(tx)):
            return "dangerous-structure"
        return None


class EdgesSortedAsText(Model):
    """Sorts the edges as strings."""

    def format_edges(self, ins: list[int], outs: list[int]) -> list[str]:
        return sorted(super().format_edges(ins, outs))


class HorizonIsTheNewestStart(Model):
    """Takes the youngest active transaction as the horizon."""

    def horizon(self) -> int:
        starts = [t.start for t in self.txs.values() if t.state == "active"]
        return int(max(starts)) if starts else self.clock


class HorizonIgnoresSerializable(Model):
    """Lets only transactions from begin() hold the horizon."""

    def horizon(self) -> int:
        starts = [t.start for t in self.txs.values() if t.state == "active" and not t.serializable]
        return int(min(starts)) if starts else self.clock


class DeadOnlyBeforeTheHorizon(Model):
    """Needs the newer version strictly before the horizon."""

    def dead(self, version: Version, limit: int) -> bool:
        return super().dead(version, limit - 1)


class VacuumKeepsOneOlderVersion(Model):
    """Keeps the version before the newest visible one as well."""

    def dead(self, version: Version, limit: int) -> bool:
        key, stamp = version[0], version[1]
        newer = [s for k, s, _, _ in self.history if k == key and stamp < s <= limit]
        return len(newer) >= 2


class VacuumIgnoresTheHorizon(Model):
    """Keeps only the newest version of every key."""

    def horizon(self) -> int:
        return self.clock if self.txs or self.history else 0

    def vacuum(self) -> list[str]:
        limit = self.clock
        gone = [v for v in self.history if super().dead(v, limit)]
        self.history = [v for v in self.history if v not in gone]
        return self.report([(key, int(stamp)) for key, stamp, _, _ in gone])


class ReportSortedAsText(Model):
    """Sorts the vacuum report as strings."""

    def report(self, gone: list[tuple[str, int]]) -> list[str]:
        return sorted(super().report(gone))


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


def test_the_hidden_cases_reach_every_commit_status():
    statuses = {
        got
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "commit"
    }
    assert statuses == {"committed", "write-conflict", "dangerous-structure", "not-active"}
