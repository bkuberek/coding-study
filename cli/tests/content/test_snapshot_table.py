"""snapshot-table promises that its hidden cases catch the classic mistakes of a table format with
snapshots: ids that start in the wrong place, scans in the wrong order, paths used twice,
manifests that forget deleted entries, overwrites that leave files behind, time travel that picks
the wrong commit at a tie, optimistic commits that refuse appends or apply a rebase to the stale
base and lose a concurrent write, conflicts missed or reported too often, expiration that deletes
a file a retained snapshot still reads or reports a file twice, and compaction that takes the
wrong files or counts as new data. These tests replay every case against a model of the table
written from the statement, which must give every expected output, and against that model with
one mistake planted at a time, which some hidden case must fail. The model copies the whole set
of live files into every snapshot, where the reference keeps one lifetime per file. A mistake
that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0337-snapshot-table"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
Files = dict[str, tuple[str, str]]


class Model:
    """The table as the statement words it: a list of snapshots, each a dict with its full set of
    live files and the files it added and removed. Each mistake below overrides one rule."""

    def __init__(self) -> None:
        self.snaps: list[dict[str, Any]] = []
        self.used: set[str] = set()
        self.expired = 0

    # --- rules
    def first_id(self) -> int:
        return 1

    def live(self, snapshot_id: int) -> Files:
        if snapshot_id < 1 or snapshot_id > len(self.snaps) or snapshot_id <= self.expired:
            return {}
        return self.snaps[snapshot_id - 1]["live"]

    def current_files(self) -> Files:
        return self.snaps[-1]["live"] if self.snaps else {}

    def paths_ok(self, files: list[list[str]]) -> bool:
        paths = [file[0] for file in files]
        return len(set(paths)) == len(paths) and not set(paths) & self.used

    def operation(self, adds: list[list[str]], removes: list[str]) -> str:
        if adds and removes:
            return "overwrite"
        return "append" if adds else "delete"

    def record(
        self, start: Files, adds: list[list[str]], removes: list[str], ts: int, op: str
    ) -> int:
        live = {p: v for p, v in start.items() if p not in removes}
        for path, partition, rows in adds:
            live[path] = (partition, rows)
            self.used.add(path)
        removed = {path: start[path] for path in removes}
        snapshot_id = len(self.snaps) + self.first_id()
        self.snaps.append(
            {
                "id": snapshot_id,
                "parent": self.parent_of(snapshot_id),
                "ts": ts,
                "op": op,
                "live": live,
                "added": {a[0]: (a[1], a[2]) for a in adds},
                "removed": removed,
            }
        )
        return snapshot_id

    def parent_of(self, snapshot_id: int) -> int:
        return snapshot_id - 1

    def ordered(self, paths: Any) -> list[str]:
        return sorted(paths)

    def status(self, snapshot: dict[str, Any], path: str) -> str:
        return "added" if path in snapshot["added"] else "existing"

    def deleted_entries(self, snapshot: dict[str, Any]) -> list[list[str]]:
        return [[path, part, rows, "deleted"] for path, (part, rows) in snapshot["removed"].items()]

    def at_time(self, timestamp: int) -> int:
        found = [s["id"] for s in self.snaps if s["ts"] <= timestamp]
        return found[-1] if found else 0

    def removable(self, paths: list[str], files: Files) -> bool:
        return len(set(paths)) == len(paths) and all(path in files for path in paths)

    def base_ok(self, base: int) -> bool:
        if base == 0:
            return self.expired == 0
        return self.expired < base <= len(self.snaps)

    def conflict_with(self, snapshot: dict[str, Any], removes: list[str], parts: set[str]) -> bool:
        twice = any(path in snapshot["removed"] for path in removes)
        return twice or self.counts_as_append(snapshot, parts)

    def counts_as_append(self, snapshot: dict[str, Any], parts: set[str]) -> bool:
        if snapshot["op"] == "replace":
            return False
        return any(part in parts for part, _ in snapshot["added"].values())

    def first_conflict(self, between: list[dict[str, Any]], hits: list[int]) -> int:
        return hits[0]

    def rebase_start(self, base: int) -> Files:
        return self.current_files()

    def expires(self, snapshot: dict[str, Any], older_than: int, keep_from: int) -> bool:
        return snapshot["ts"] < older_than and snapshot["id"] < keep_from

    def freed(self, gone: list[dict[str, Any]], kept: list[dict[str, Any]]) -> set[str]:
        before = {path for snapshot in gone for path in snapshot["live"]}
        still = {path for snapshot in kept for path in snapshot["live"]}
        return before - still

    def small(self, rows: str, limit: int) -> bool:
        return int(rows) < limit

    def compacted_path(self, partition: str) -> str:
        return f"{partition}/compacted-{len(self.snaps) + 1}"

    # --- level 1
    def append(self, files: list[list[str]], timestamp: int) -> int:
        if not files or not self.paths_ok(files):
            return -1
        return self.record(self.current_files(), files, [], timestamp, "append")

    def current_snapshot(self) -> int:
        return self.snaps[-1]["id"] if self.snaps else 0

    def scan(self) -> list[str]:
        return self.ordered(self.current_files())

    def manifest(self, snapshot_id: int) -> list[list[str]]:
        if not self.live(snapshot_id) and not (self.expired < snapshot_id <= len(self.snaps)):
            return []
        snapshot = self.snaps[snapshot_id - 1]
        entries = [
            [path, part, rows, self.status(snapshot, path)]
            for path, (part, rows) in snapshot["live"].items()
        ]
        entries += self.deleted_entries(snapshot)
        order = {path: rank for rank, path in enumerate(self.ordered(e[0] for e in entries))}
        return sorted(entries, key=lambda entry: order[entry[0]])

    # --- level 2
    def delete_files(self, paths: list[str], timestamp: int) -> int:
        if not paths or not self.removable(paths, self.current_files()):
            return -1
        return self.record(self.current_files(), [], paths, timestamp, "delete")

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        if any(file[1] != partition for file in files) or not self.paths_ok(files):
            return -1
        old = [p for p, (part, _) in self.current_files().items() if part == partition]
        if not old and not files:
            return -1
        op = self.operation(files, old)
        return self.record(self.current_files(), files, old, timestamp, op)

    def scan_at(self, snapshot_id: int) -> list[str]:
        return self.ordered(self.live(snapshot_id))

    def snapshot_as_of(self, timestamp: int) -> int:
        found = self.at_time(timestamp)
        return found if found > self.expired else 0

    def history(self) -> list[list[str]]:
        return [
            [
                str(s["id"]),
                str(s["parent"]),
                str(s["ts"]),
                s["op"],
                str(len(s["added"])),
                str(len(s["removed"])),
            ]
            for s in self.snaps[self.expired :]
        ]

    # --- level 3
    def commit(
        self, base: int, adds: list[list[str]], removes: list[str], timestamp: int
    ) -> list[str]:
        if not self.base_ok(base) or not (adds or removes) or not self.paths_ok(adds):
            return ["invalid", ""]
        start = self.snaps[base - 1]["live"] if base else {}
        if not self.removable(removes, start):
            return ["invalid", ""]
        parts = {start[path][0] for path in removes}
        between = self.snaps[base:]
        hits = [s["id"] for s in between if self.conflict_with(s, removes, parts)]
        if hits:
            return ["conflict", str(self.first_conflict(between, hits))]
        outcome = "committed" if base == len(self.snaps) else "rebased"
        op = self.operation(adds, removes)
        return [outcome, str(self.record(self.rebase_start(base), adds, removes, timestamp, op))]

    # --- level 4
    def expire_snapshots(self, older_than: int, retain_last: int) -> list[str]:
        keep_from = len(self.snaps) - retain_last + 1
        retained = self.snaps[self.expired :]
        gone = []
        for snapshot in retained:
            if not self.expires(snapshot, older_than, keep_from):
                break
            gone.append(snapshot)
        self.expired += len(gone)
        return sorted(self.freed(gone, self.snaps[self.expired :]))

    def compact(self, partition: str, max_file_rows: int, timestamp: int) -> int:
        files = self.current_files()
        chosen = [
            path
            for path, (part, rows) in files.items()
            if part == partition and self.small(rows, max_file_rows)
        ]
        if len(chosen) < 2:
            return -1
        total = sum(int(files[path][1]) for path in chosen)
        added = [[self.compacted_path(partition), partition, str(total)]]
        return self.record(files, added, chosen, timestamp, "replace")


# ------------------------------------------------------------------ level 1 mistakes
class IdsStartAtZero(Model):
    """Numbers the first snapshot 0."""

    def first_id(self) -> int:
        return 0

    def live(self, snapshot_id: int) -> Files:
        return super().live(snapshot_id + 1)

    def current_snapshot(self) -> int:
        return self.snaps[-1]["id"] if self.snaps else -1


class ScanInInsertionOrder(Model):
    """Lists files in the order they were added."""

    def ordered(self, paths: Any) -> list[str]:
        return list(paths)


class ScanIgnoringCase(Model):
    """Sorts paths without regard to case."""

    def ordered(self, paths: Any) -> list[str]:
        return sorted(paths, key=lambda path: (path.lower(), path))


class PathsMayRepeatAcrossCommits(Model):
    """Checks only that a path is not live, not that it was never used."""

    def paths_ok(self, files: list[list[str]]) -> bool:
        paths = [file[0] for file in files]
        return len(set(paths)) == len(paths) and not set(paths) & set(self.current_files())


class DuplicatesInOneCallAccepted(Model):
    """Accepts a path twice in one call; the last row wins."""

    def paths_ok(self, files: list[list[str]]) -> bool:
        return not {file[0] for file in files} & self.used


class EverythingIsAdded(Model):
    """Marks every file of a manifest as added."""

    def status(self, snapshot: dict[str, Any], path: str) -> str:
        return "added"


# ------------------------------------------------------------------ level 2 mistakes
class ManifestForgetsDeletedFiles(Model):
    """Leaves out the files a snapshot removed."""

    def deleted_entries(self, snapshot: dict[str, Any]) -> list[list[str]]:
        return []


class DeleteSkipsMissingFiles(Model):
    """Deletes the paths that are live and ignores the others."""

    def delete_files(self, paths: list[str], timestamp: int) -> int:
        live = [path for path in dict.fromkeys(paths) if path in self.current_files()]
        return super().delete_files(live, timestamp) if live else -1


class OverwriteKeepsTheOldFiles(Model):
    """Adds the new files and keeps the partition's old ones."""

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        if any(file[1] != partition for file in files) or not self.paths_ok(files):
            return -1
        if not files:
            return -1
        return self.record(self.current_files(), files, [], timestamp, "append")


class OverwriteOfNothingCommits(Model):
    """Commits an overwrite that changes nothing."""

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        has_old = any(part == partition for part, _ in self.current_files().values())
        if not has_old and not files and self.paths_ok(files):
            return self.record(self.current_files(), [], [], timestamp, "overwrite")
        return super().overwrite(partition, files, timestamp)


class OverwriteAcceptsOtherPartitions(Model):
    """Accepts files of another partition in an overwrite."""

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        moved = [[path, partition, rows] for path, _, rows in files]
        return super().overwrite(partition, moved, timestamp)


class OverwriteIsAlwaysOverwrite(Model):
    """Names every overwrite operation overwrite, even when it only adds or only removes."""

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        snapshot_id = super().overwrite(partition, files, timestamp)
        if snapshot_id > 0:
            self.snaps[-1]["op"] = "overwrite"
        return snapshot_id


class TimeTravelBeforeTheTime(Model):
    """Picks the last commit strictly before the time."""

    def at_time(self, timestamp: int) -> int:
        return super().at_time(timestamp - 1)


class TimeTravelFirstCommitAtATie(Model):
    """Picks the first of the commits made at the latest time."""

    def at_time(self, timestamp: int) -> int:
        found = super().at_time(timestamp)
        if not found:
            return 0
        tied = [s["id"] for s in self.snaps if s["ts"] == self.snaps[found - 1]["ts"]]
        return tied[0]


# ------------------------------------------------------------------ level 3 mistakes
class StaleAppendConflicts(Model):
    """Rejects any commit whose base is not the current snapshot."""

    def conflict_with(self, snapshot: dict[str, Any], removes: list[str], parts: set[str]) -> bool:
        return True


class RebaseOntoTheBase(Model):
    """Applies a rebased commit to the files of its base, losing concurrent changes."""

    def rebase_start(self, base: int) -> Files:
        return self.snaps[base - 1]["live"] if base else {}


class RebasedParentIsTheBase(Model):
    """Records the base as the parent of a rebased snapshot."""

    def commit(
        self, base: int, adds: list[list[str]], removes: list[str], timestamp: int
    ) -> list[str]:
        answer = super().commit(base, adds, removes, timestamp)
        if answer[0] == "rebased":
            self.snaps[-1]["parent"] = base
        return answer


class RemovedTwiceGoesUnnoticed(Model):
    """Never checks whether a file was removed since the base."""

    def conflict_with(self, snapshot: dict[str, Any], removes: list[str], parts: set[str]) -> bool:
        return self.counts_as_append(snapshot, parts)


class ConcurrentAppendsGoUnnoticed(Model):
    """Never checks for files added to the partitions it removes from."""

    def conflict_with(self, snapshot: dict[str, Any], removes: list[str], parts: set[str]) -> bool:
        return any(path in snapshot["removed"] for path in removes)


class AnyChangeInThePartitionConflicts(Model):
    """Also conflicts when a concurrent commit removed another file of the partition."""

    def conflict_with(self, snapshot: dict[str, Any], removes: list[str], parts: set[str]) -> bool:
        touched = any(part in parts for part, _ in snapshot["removed"].values())
        return touched or super().conflict_with(snapshot, removes, parts)


class LastConflictReported(Model):
    """Reports the latest conflicting snapshot instead of the first."""

    def first_conflict(self, between: list[dict[str, Any]], hits: list[int]) -> int:
        return hits[-1]


class RemovalsCheckedAgainstCurrent(Model):
    """Requires removed files to be live now, so a lost race is invalid instead of a conflict."""

    def commit(
        self, base: int, adds: list[list[str]], removes: list[str], timestamp: int
    ) -> list[str]:
        if self.base_ok(base) and not self.removable(removes, self.current_files()):
            return ["invalid", ""]
        return super().commit(base, adds, removes, timestamp)


class BaseZeroRemovesFromCurrent(Model):
    """Reads base 0 as the current snapshot."""

    def commit(
        self, base: int, adds: list[list[str]], removes: list[str], timestamp: int
    ) -> list[str]:
        if base == 0 and self.snaps and self.base_ok(0):
            base = len(self.snaps)
        return super().commit(base, adds, removes, timestamp)


# ------------------------------------------------------------------ level 4 mistakes
class RetainLastIgnored(Model):
    """Expires by age alone, except the current snapshot."""

    def expires(self, snapshot: dict[str, Any], older_than: int, keep_from: int) -> bool:
        return snapshot["ts"] < older_than and snapshot["id"] < len(self.snaps)


class CutoffIsInclusive(Model):
    """Expires a snapshot made exactly at the cutoff."""

    def expires(self, snapshot: dict[str, Any], older_than: int, keep_from: int) -> bool:
        return snapshot["ts"] <= older_than and snapshot["id"] < keep_from


class FreesFilesStillLive(Model):
    """Frees a file that the current snapshot no longer reads, though an older retained one does."""

    def freed(self, gone: list[dict[str, Any]], kept: list[dict[str, Any]]) -> set[str]:
        return super().freed(gone, kept) | {
            path for snapshot in gone for path in snapshot["live"] if path not in kept[-1]["live"]
        }


class FreesOnlyWhatExpiredSnapshotsRemoved(Model):
    """Frees only the files that the expired snapshots themselves removed."""

    def freed(self, gone: list[dict[str, Any]], kept: list[dict[str, Any]]) -> set[str]:
        return {path for snapshot in gone for path in snapshot["removed"]}


class FreedFilesReportedAgain(Model):
    """Reports every file no retained snapshot reads, including ones reported before."""

    def expire_snapshots(self, older_than: int, retain_last: int) -> list[str]:
        super().expire_snapshots(older_than, retain_last)
        ever = {path for snapshot in self.snaps[: self.expired] for path in snapshot["live"]}
        still = {path for snapshot in self.snaps[self.expired :] for path in snapshot["live"]}
        return sorted(ever - still)


class ExpiredBaseAccepted(Model):
    """Accepts a base that has expired."""

    def base_ok(self, base: int) -> bool:
        return 0 <= base <= len(self.snaps)


class TimeTravelSkipsToTheOldestRetained(Model):
    """Answers a time before the retained snapshots with the oldest retained one."""

    def snapshot_as_of(self, timestamp: int) -> int:
        found = self.at_time(timestamp)
        return max(found, self.expired + 1) if found else 0


class CompactionIncludesTheLimit(Model):
    """Counts a file with exactly the limit of rows as small."""

    def small(self, rows: str, limit: int) -> bool:
        return int(rows) <= limit


class CompactionOfOneFile(Model):
    """Rewrites a single small file too."""

    def compact(self, partition: str, max_file_rows: int, timestamp: int) -> int:
        files = self.current_files()
        chosen = [
            p
            for p, (part, rows) in files.items()
            if part == partition and self.small(rows, max_file_rows)
        ]
        if len(chosen) == 1:
            total = files[chosen[0]][1]
            added = [[self.compacted_path(partition), partition, total]]
            return self.record(files, added, chosen, timestamp, "replace")
        return super().compact(partition, max_file_rows, timestamp)


class CompactionNamedAfterTheParent(Model):
    """Names the compacted file after the current snapshot instead of the new one."""

    def compacted_path(self, partition: str) -> str:
        return f"{partition}/compacted-{len(self.snaps)}"


class CompactionCountsAsAnAppend(Model):
    """Treats a compaction like any commit that added files."""

    def counts_as_append(self, snapshot: dict[str, Any], parts: set[str]) -> bool:
        return any(part in parts for part, _ in snapshot["added"].values())


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


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


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_give_every_commit_outcome():
    outcomes = {
        got[0]
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "commit"
    }
    assert outcomes == {"committed", "rebased", "conflict", "invalid"}
