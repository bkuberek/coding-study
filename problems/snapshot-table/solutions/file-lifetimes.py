NEVER = 1 << 62


class _File:
    __slots__ = ("path", "partition", "rows", "added", "removed")

    def __init__(self, path: str, partition: str, rows: str, added: int) -> None:
        self.path = path
        self.partition = partition
        self.rows = rows
        self.added = added
        self.removed = NEVER

    def live_at(self, snapshot: int) -> bool:
        return self.added <= snapshot < self.removed


class _Snapshot:
    __slots__ = ("snapshot_id", "parent", "timestamp", "operation", "added", "removed")

    def __init__(self, snapshot_id: int, parent: int, timestamp: int, operation: str) -> None:
        self.snapshot_id = snapshot_id
        self.parent = parent
        self.timestamp = timestamp
        self.operation = operation
        self.added: list[_File] = []
        self.removed: list[_File] = []


class SnapshotTable:
    """Snapshots are numbered 1, 2, 3 in commit order, and history is a single line, so a data
    file is live in one interval of snapshots: from the one that added it up to, not including,
    the one that removed it. Each file keeps that interval, each snapshot keeps the files it added
    and removed, and every question is a filter over the files or a walk over the snapshots."""

    def __init__(self) -> None:
        self._files: dict[str, _File] = {}
        self._snapshots: list[_Snapshot] = []
        self._first_retained = 1

    # Level 1
    def append(self, files: list[list[str]], timestamp: int) -> int:
        if not files or not self._fresh(files):
            return -1
        return self._commit(files, [], timestamp)

    def current_snapshot(self) -> int:
        return len(self._snapshots)

    def scan(self) -> list[str]:
        return self.scan_at(self.current_snapshot())

    def manifest(self, snapshot_id: int) -> list[list[str]]:
        if not self._retained(snapshot_id):
            return []
        entries = []
        for file in self._files.values():
            if file.live_at(snapshot_id):
                status = "added" if file.added == snapshot_id else "existing"
            elif file.removed == snapshot_id:
                status = "deleted"
            else:
                continue
            entries.append([file.path, file.partition, file.rows, status])
        return sorted(entries)

    # Level 2
    def delete_files(self, paths: list[str], timestamp: int) -> int:
        current = self.current_snapshot()
        if not paths or not self._removable(paths, current):
            return -1
        return self._commit([], paths, timestamp)

    def overwrite(self, partition: str, files: list[list[str]], timestamp: int) -> int:
        if any(file[1] != partition for file in files) or not self._fresh(files):
            return -1
        current = self.current_snapshot()
        old = [f.path for f in self._files.values() if f.partition == partition and f.live_at(current)]
        if not old and not files:
            return -1
        return self._commit(files, old, timestamp)

    def scan_at(self, snapshot_id: int) -> list[str]:
        if not self._retained(snapshot_id):
            return []
        return sorted(path for path, file in self._files.items() if file.live_at(snapshot_id))

    def snapshot_as_of(self, timestamp: int) -> int:
        found = 0
        for snapshot in self._snapshots:
            if snapshot.timestamp <= timestamp:
                found = snapshot.snapshot_id
        return found if found >= self._first_retained else 0

    def history(self) -> list[list[str]]:
        return [
            [
                str(s.snapshot_id),
                str(s.parent),
                str(s.timestamp),
                s.operation,
                str(len(s.added)),
                str(len(s.removed)),
            ]
            for s in self._snapshots[self._first_retained - 1 :]
        ]

    # Level 3
    def commit(
        self, base: int, adds: list[list[str]], removes: list[str], timestamp: int
    ) -> list[str]:
        current = self.current_snapshot()
        base_ok = base == 0 and self._first_retained == 1 or self._retained(base)
        if not base_ok or not (adds or removes):
            return ["invalid", ""]
        if not self._fresh(adds) or not self._removable(removes, base):
            return ["invalid", ""]
        removing = set(removes)
        partitions = {self._files[path].partition for path in removes}
        for snapshot in self._snapshots[base:current]:
            removed_twice = any(file.path in removing for file in snapshot.removed)
            appended = snapshot.operation != "replace" and any(
                file.partition in partitions for file in snapshot.added
            )
            if removed_twice or appended:
                return ["conflict", str(snapshot.snapshot_id)]
        outcome = "committed" if base == current else "rebased"
        return [outcome, str(self._commit(adds, removes, timestamp))]

    # Level 4
    def expire_snapshots(self, older_than: int, retain_last: int) -> list[str]:
        old_first = self._first_retained
        last_candidate = self.current_snapshot() - retain_last
        while (
            self._first_retained <= last_candidate
            and self._snapshots[self._first_retained - 1].timestamp < older_than
        ):
            self._first_retained += 1
        new_first = self._first_retained
        return sorted(
            path for path, file in self._files.items() if old_first < file.removed <= new_first
        )

    def compact(self, partition: str, max_file_rows: int, timestamp: int) -> int:
        current = self.current_snapshot()
        small = [
            file.path
            for file in self._files.values()
            if file.partition == partition
            and file.live_at(current)
            and int(file.rows) < max_file_rows
        ]
        if len(small) < 2:
            return -1
        rows = sum(int(self._files[path].rows) for path in small)
        path = f"{partition}/compacted-{current + 1}"
        return self._commit([[path, partition, str(rows)]], small, timestamp, "replace")

    # Helpers
    def _retained(self, snapshot_id: int) -> bool:
        return self._first_retained <= snapshot_id <= self.current_snapshot()

    def _fresh(self, files: list[list[str]]) -> bool:
        paths = [file[0] for file in files]
        return len(set(paths)) == len(paths) and not any(path in self._files for path in paths)

    def _removable(self, paths: list[str], snapshot_id: int) -> bool:
        if len(set(paths)) != len(paths):
            return False
        return all(path in self._files and self._files[path].live_at(snapshot_id) for path in paths)

    def _commit(
        self,
        adds: list[list[str]],
        removes: list[str],
        timestamp: int,
        operation: str | None = None,
    ) -> int:
        parent = self.current_snapshot()
        snapshot_id = parent + 1
        if operation is None:
            operation = "overwrite" if adds and removes else "append" if adds else "delete"
        snapshot = _Snapshot(snapshot_id, parent, timestamp, operation)
        for path in removes:
            self._files[path].removed = snapshot_id
            snapshot.removed.append(self._files[path])
        for path, partition, rows in adds:
            file = _File(path, partition, rows, snapshot_id)
            self._files[path] = file
            snapshot.added.append(file)
        self._snapshots.append(snapshot)
        return snapshot_id
