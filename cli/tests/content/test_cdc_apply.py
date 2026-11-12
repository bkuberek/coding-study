"""cdc-apply promises that its hidden cases catch the classic mistakes of applying a change log to
a replica: inserts that overwrite, updates that insert, keys sorted as numbers or without case, a
single position for the whole replica, deletes that forget their version, rejected changes that
move it, transactions that show early or apply in part, replayed commits taken for new ones, a
snapshot that lets old changes back in, schema changes checked before they are skipped, and a
comparison that matches columns by position or mixes up its sides. These tests replay every case
against a model of the replica written from the statement, which must give every expected output,
and against that model with one mistake planted at a time, which some hidden case must fail. The
model keeps one record per key and applies a transaction to a full copy of the table. A mistake
that crashes fails its case, as a thrown exception does in the grader."""

import copy
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0333-cdc-apply"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

OK, SKIPPED = "ok", "skipped"


class Record:
    """One key of the replica: its row (None once deleted) and its version (-1 if never changed)."""

    def __init__(self) -> None:
        self.row: list[str] | None = None
        self.version = -1


class Model:
    """The replica as the statement words it, one rule per method."""

    def __init__(self, columns: list[str]) -> None:
        self.names = list(columns)
        self.records: dict[str, Record] = {}
        self.floor = 0
        self.schema_version = 0
        self.buffers: dict[str, list[tuple[str, list[str]]]] = {}

    # --- shared rules
    def record(self, records: dict[str, Record], key: str) -> Record:
        return records.setdefault(key, Record())

    def present(self, records: dict[str, Record], key: str) -> bool:
        return key in records and records[key].row is not None

    def width_ok(self, op: str, row: list[str]) -> bool:
        return op == "delete" or len(row) == len(self.names)

    def code(self, records: dict[str, Record], op: str, row: list[str]) -> str:
        if not self.width_ok(op, row):
            return "column-count"
        here = self.present(records, row[0])
        if op == "insert":
            return "duplicate-key" if here else OK
        return OK if here else "unknown-key"

    def do(self, records: dict[str, Record], op: str, row: list[str]) -> None:
        self.record(records, row[0]).row = None if op == "delete" else list(row)

    def order(self, keys: Any) -> list[str]:
        return sorted(keys)

    def stale(self, lsn: int, version: int) -> bool:
        return lsn <= version

    def below_floor(self, lsn: int) -> bool:
        return lsn <= self.floor

    def version_of(self, key: str) -> int:
        return self.records[key].version if key in self.records else -1

    # --- level 1
    def apply(self, op: str, row: list[str]) -> str:
        result = self.code(self.records, op, row)
        if result == OK:
            self.do(self.records, op, row)
        return result

    def rows(self) -> list[list[str]]:
        live = {k: r.row for k, r in self.records.items() if r.row is not None}
        return [list(live[k]) for k in self.order(live)]

    # --- level 2
    def apply_at(self, lsn: int, op: str, row: list[str]) -> str:
        if self.below_floor(lsn) or self.stale(lsn, self.version_of(row[0])):
            return SKIPPED
        result = self.apply(op, row)
        if result == OK:
            self.set_version(self.records, row[0], lsn, op)
        return result

    def set_version(self, records: dict[str, Record], key: str, lsn: int, op: str) -> None:
        self.record(records, key).version = lsn

    def version(self, key: str) -> int:
        return self.version_of(key)

    # --- level 3
    def snapshot_version(self, lsn: int) -> int:
        return lsn

    def load_snapshot(self, lsn: int, snapshot: list[list[str]]) -> None:
        self.records = {}
        for row in snapshot:
            record = self.record(self.records, row[0])
            record.row = list(row)
            record.version = self.snapshot_version(lsn)
        self.floor = lsn

    def stage(self, tx: str, op: str, row: list[str]) -> None:
        self.buffers.setdefault(tx, []).append((op, list(row)))

    def take(self, tx: str) -> list[tuple[str, list[str]]]:
        return self.buffers.pop(tx, [])

    def commit(self, lsn: int, tx: str) -> str:
        changes = self.take(tx)
        if self.below_floor(lsn):
            return SKIPPED
        before = {key: record.version for key, record in self.records.items()}
        work = copy.deepcopy(self.records)
        applied = []
        for op, row in changes:
            if self.stale(lsn, before.get(row[0], -1)):
                continue
            result = self.code(self.view(work), op, row)
            if result != OK:
                return result
            self.do(work, op, row)
            applied.append((op, row[0]))
        if not applied:
            return self.all_skipped()
        for op, key in applied:
            self.set_version(work, key, lsn, op)
        self.records = work
        return OK

    def view(self, work: dict[str, Record]) -> dict[str, Record]:
        return work

    def all_skipped(self) -> str:
        return SKIPPED

    def rollback(self, tx: str) -> None:
        self.buffers.pop(tx, None)

    # --- level 4
    def alter_at(self, lsn: int, change: list[str]) -> str:
        if self.below_floor(lsn) or self.stale(lsn, self.schema_version):
            return SKIPPED
        result = self.alter(change)
        if result == OK:
            self.schema_version = lsn
        return result

    def rows_with_names(self) -> list[dict[str, str]]:
        return [dict(zip(self.names, row, strict=True)) for _, row in self.live()]

    def live(self) -> list[tuple[Record, list[str]]]:
        return [(r, r.row) for r in self.records.values() if r.row is not None]

    def alter(self, change: list[str]) -> str:
        kind = change[0]
        named = self.rows_with_names()
        if kind == "add":
            if change[1] in self.names:
                return "duplicate-column"
            self.names.append(change[1])
            for values in named:
                values[change[1]] = self.default(change[2])
        elif change[1] not in self.names:
            return "unknown-column"
        elif kind == "drop":
            if change[1] == self.names[0]:
                return "key-column"
            self.names.remove(change[1])
        else:
            if self.taken(change[1], change[2]):
                return "duplicate-column"
            self.names[self.names.index(change[1])] = change[2]
            for values in named:
                values[change[2]] = values[change[1]]
        for (record, _), values in zip(self.live(), named, strict=True):
            record.row = [values[name] for name in self.names]
        return OK

    def default(self, value: str) -> str:
        return value

    def taken(self, old: str, new: str) -> bool:
        return new in self.names

    def columns(self) -> list[str]:
        return list(self.names)

    def column_rows(self, theirs: list[str]) -> list[list[str]]:
        names = set(self.names) | set(theirs)
        rows = []
        for name in sorted(names):
            if name not in self.names:
                rows.append(["missing-column", name])
            elif name not in theirs:
                rows.append(["extra-column", name])
        return rows

    def lookup(self, names: list[str], row: list[str], name: str) -> str:
        return row[names.index(name)]

    def compare(self, source_columns: list[str], source_rows: list[list[str]]) -> list[list[str]]:
        report = self.column_rows(source_columns)
        common = sorted(set(self.names) & set(source_columns))
        mine = {row[0]: row for _, row in self.live()}
        theirs = {row[0]: row for row in source_rows}
        for key in sorted(set(mine) | set(theirs)):
            if key not in mine:
                report.append(["missing-row", key])
            elif key not in theirs:
                report.append(["extra-row", key])
            else:
                for name in common:
                    here = self.lookup(self.names, mine[key], name)
                    there = self.lookup(source_columns, theirs[key], name)
                    if here != there:
                        report.append(["value-differs", key, name, here, there])
        return report


# ------------------------------------------------------------------ level 1 mistakes
class InsertOverwrites(Model):
    """Lets an insert replace a row that exists."""

    def code(self, records: dict[str, Record], op: str, row: list[str]) -> str:
        result = super().code(records, op, row)
        return OK if result == "duplicate-key" else result


class UpdateInserts(Model):
    """Lets an update of a missing key insert it."""

    def code(self, records: dict[str, Record], op: str, row: list[str]) -> str:
        result = super().code(records, op, row)
        return OK if result == "unknown-key" and op == "update" else result


class DeleteOfMissingIsOk(Model):
    """Answers ok to the delete of a key that is not there."""

    def code(self, records: dict[str, Record], op: str, row: list[str]) -> str:
        result = super().code(records, op, row)
        return OK if result == "unknown-key" and op == "delete" else result


class KeysIgnoreCase(Model):
    """Sorts keys without regard to case."""

    def order(self, keys: Any) -> list[str]:
        return sorted(keys, key=str.lower)


class RowsInArrivalOrder(Model):
    """Lists rows in the order their keys first appeared."""

    def order(self, keys: Any) -> list[str]:
        return [k for k in self.records if k in set(keys)]


class UpdateKeepsOldValuesForEmpty(Model):
    """Reads an empty value in an update as 'unchanged'."""

    def do(self, records: dict[str, Record], op: str, row: list[str]) -> None:
        old = records[row[0]].row if self.present(records, row[0]) else None
        if op == "update" and old is not None:
            row = [new or before for new, before in zip(row, old, strict=True)]
        super().do(records, op, row)


# ------------------------------------------------------------------ level 2 mistakes
class OnePositionForAll(Model):
    """Keeps one position for the whole replica instead of a version per key."""

    def __init__(self, columns: list[str]) -> None:
        super().__init__(columns)
        self.position = -1

    def apply_at(self, lsn: int, op: str, row: list[str]) -> str:
        if lsn <= self.position:
            return SKIPPED
        result = super().apply_at(lsn, op, row)
        if result == OK:
            self.position = lsn
        return result


class DeleteForgetsTheVersion(Model):
    """Removes a key's version together with its row."""

    def set_version(self, records: dict[str, Record], key: str, lsn: int, op: str) -> None:
        if op == "delete":
            records.pop(key, None)
        else:
            super().set_version(records, key, lsn, op)


class EqualPositionApplies(Model):
    """Skips only changes strictly below the version, so a duplicate applies again."""

    def stale(self, lsn: int, version: int) -> bool:
        return lsn < version


class RejectedChangeMovesTheVersion(Model):
    """Records the position of a change even when it was rejected."""

    def apply_at(self, lsn: int, op: str, row: list[str]) -> str:
        result = super().apply_at(lsn, op, row)
        if result not in (OK, SKIPPED):
            self.record(self.records, row[0]).version = lsn
        return result


class UnknownVersionIsZero(Model):
    """Reports 0 as the version of a key that was never changed."""

    def version(self, key: str) -> int:
        return max(0, super().version(key))


# ------------------------------------------------------------------ level 3 mistakes
class StagedChangesApplyAtOnce(Model):
    """Applies a staged change right away."""

    def stage(self, tx: str, op: str, row: list[str]) -> None:
        self.apply(op, row)


class CommitAppliesUpToTheError(Model):
    """Keeps the changes of a transaction that come before its first error."""

    def commit(self, lsn: int, tx: str) -> str:
        changes = self.take(tx)
        if self.below_floor(lsn):
            return SKIPPED
        for op, row in changes:
            if self.stale(lsn, self.version_of(row[0])):
                continue
            result = self.apply(op, row)
            if result != OK:
                return result
            self.set_version(self.records, row[0], lsn, op)
        return OK


class TransactionSeesOnlyTheTable(Model):
    """Checks each change of a transaction against the table as it was before the commit."""

    def view(self, work: dict[str, Record]) -> dict[str, Record]:
        return self.records


class ReplayedCommitIsOk(Model):
    """Answers ok to a commit whose changes were all skipped."""

    def all_skipped(self) -> str:
        return OK


class CommitKeepsOldVersions(Model):
    """Leaves the keys of a transaction at their versions from before it."""

    def commit(self, lsn: int, tx: str) -> str:
        before = {key: record.version for key, record in self.records.items()}
        result = super().commit(lsn, tx)
        for key, version in before.items():
            if key in self.records:
                self.records[key].version = version
        return result


class DeletedKeysKeepOldVersions(Model):
    """Gives the commit's position to the keys a transaction wrote, but not to those it deleted."""

    def set_version(self, records: dict[str, Record], key: str, lsn: int, op: str) -> None:
        if op != "delete" or not hasattr(self, "committing"):
            super().set_version(records, key, lsn, op)

    def commit(self, lsn: int, tx: str) -> str:
        self.committing = True
        try:
            return super().commit(lsn, tx)
        finally:
            del self.committing


class OneNewerKeySkipsTheTransaction(Model):
    """Skips the whole transaction when any of its keys is newer than the commit."""

    def commit(self, lsn: int, tx: str) -> str:
        changes = self.buffers.get(tx, [])
        if any(self.stale(lsn, self.version_of(row[0])) for _, row in changes):
            self.take(tx)
            return SKIPPED
        return super().commit(lsn, tx)


class FloorIsExclusive(Model):
    """Skips only what is strictly below the snapshot's position."""

    def below_floor(self, lsn: int) -> bool:
        return lsn < self.floor


class FloorOnlyForSnapshotRows(Model):
    """Protects only the keys the snapshot holds, so an old change of another key applies."""

    def below_floor(self, lsn: int) -> bool:
        return False


class SnapshotRowsHaveVersionZero(Model):
    """Gives the snapshot's rows the version 0."""

    def snapshot_version(self, lsn: int) -> int:
        return 0


class RollbackIsIgnored(Model):
    """Keeps the changes of a rolled back transaction for the next one of that name."""

    def rollback(self, tx: str) -> None:
        pass


class CommitKeepsTheBuffer(Model):
    """Leaves the changes of a committed transaction staged for the next one of that name."""

    def take(self, tx: str) -> list[tuple[str, list[str]]]:
        return list(self.buffers.get(tx, []))


# ------------------------------------------------------------------ level 4 mistakes
class AddLeavesRowsShort(Model):
    """Gives the existing rows an empty value in a new column instead of its default."""

    def default(self, value: str) -> str:
        return ""


class DropRemovesTheLastValue(Model):
    """Removes the last value of every row instead of the dropped column's."""

    def alter(self, change: list[str]) -> str:
        if change[0] == "drop" and change[1] in self.names[1:]:
            self.names.remove(change[1])
            for record, row in self.live():
                record.row = row[:-1]
            return OK
        return super().alter(change)


class SchemaChecksBeforeSkipping(Model):
    """Validates a schema change before it tests the schema's version."""

    def alter_at(self, lsn: int, change: list[str]) -> str:
        names = list(self.names)
        records = copy.deepcopy(self.records)
        result = self.alter(change)
        if result != OK:
            return result
        self.names, self.records = names, records
        return super().alter_at(lsn, change)


class SchemaIgnoresTheFloor(Model):
    """Applies a schema change at or below the snapshot's position."""

    def alter_at(self, lsn: int, change: list[str]) -> str:
        if self.stale(lsn, self.schema_version):
            return SKIPPED
        result = self.alter(change)
        if result == OK:
            self.schema_version = lsn
        return result


class KeyColumnCanBeDropped(Model):
    """Lets the key's column be dropped."""

    def alter(self, change: list[str]) -> str:
        if change[0] == "drop" and self.names and change[1] == self.names[0]:
            self.names = self.names[1:]
            for record, row in self.live():
                record.row = row[1:]
            return OK
        return super().alter(change)


class RenameToItselfIsOk(Model):
    """Accepts renaming a column to its own name."""

    def taken(self, old: str, new: str) -> bool:
        return new != old and new in self.names


class WidthCheckedOnInsertsOnly(Model):
    """Counts the values of inserts but not of updates."""

    def width_ok(self, op: str, row: list[str]) -> bool:
        return op != "insert" or len(row) == len(self.names)

    def do(self, records: dict[str, Record], op: str, row: list[str]) -> None:
        if op == "update":
            row = (row + [""] * len(self.names))[: len(self.names)]
        super().do(records, op, row)


class WidthCheckedBeforeSkipping(Model):
    """Counts a row's values before it tests the key's version."""

    def apply_at(self, lsn: int, op: str, row: list[str]) -> str:
        if not self.width_ok(op, row):
            return "column-count"
        return super().apply_at(lsn, op, row)


class CompareByPosition(Model):
    """Reads the source's values by the replica's column positions."""

    def lookup(self, names: list[str], row: list[str], name: str) -> str:
        return row[self.names.index(name)]


class CompareSidesSwapped(Model):
    """Calls missing what only the replica has, and extra what only the source has."""

    def compare(self, source_columns: list[str], source_rows: list[list[str]]) -> list[list[str]]:
        flip = {
            "missing-row": "extra-row",
            "extra-row": "missing-row",
            "missing-column": "extra-column",
            "extra-column": "missing-column",
        }
        report = super().compare(source_columns, source_rows)
        return [[flip.get(row[0], row[0]), *row[1:]] for row in report]


class CompareValuesSwapped(Model):
    """Lists the source's value before the replica's."""

    def compare(self, source_columns: list[str], source_rows: list[list[str]]) -> list[list[str]]:
        report = super().compare(source_columns, source_rows)
        return [[*r[:3], r[4], r[3]] if r[0] == "value-differs" else r for r in report]


class CompareSeesStagedChanges(Model):
    """Compares the table with every open transaction applied."""

    def compare(self, source_columns: list[str], source_rows: list[list[str]]) -> list[list[str]]:
        saved = copy.deepcopy(self.records)
        for changes in self.buffers.values():
            for op, row in changes:
                if self.code(self.records, op, row) == OK:
                    self.do(self.records, op, row)
        report = super().compare(source_columns, source_rows)
        self.records = saved
        return report


class CompareColumnsGroupedByKind(Model):
    """Lists every missing column before every extra one."""

    def column_rows(self, theirs: list[str]) -> list[list[str]]:
        rows = super().column_rows(theirs)
        return sorted(rows, key=lambda row: (row[0] != "missing-column", row[1]))


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
    except (IndexError, KeyError, ValueError, TypeError, AssertionError):
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


def test_every_result_code_appears_in_a_hidden_case():
    codes = set()
    for case in HIDDEN_CASES:
        codes |= {got for got in case["expected"] if isinstance(got, str)}
    assert codes == {
        "ok",
        "skipped",
        "duplicate-key",
        "unknown-key",
        "column-count",
        "duplicate-column",
        "unknown-column",
        "key-column",
    }
