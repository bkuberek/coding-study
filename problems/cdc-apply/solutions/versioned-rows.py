OK = "ok"
SKIPPED = "skipped"
NEVER = -1


class ReplicaTable:
    """A dictionary from key to row holds the table. A second dictionary holds each key's version,
    the position at which its last change became visible, and keeps it when the row is deleted:
    that tombstone is what stops an old insert from bringing a deleted row back.

    A change is skipped when its position is not after the key's version, or not after the
    snapshot the table started from. A transaction's changes wait in a buffer until its commit,
    then run into an overlay, a small dictionary of the rows they change, which is written into
    the table only when every change worked.
    """

    def __init__(self, columns: list[str]) -> None:
        self._columns = list(columns)
        self._rows: dict[str, list[str]] = {}
        self._versions: dict[str, int] = {}
        self._floor = 0
        self._schema_version = 0
        self._staged: dict[str, list[tuple[str, list[str]]]] = {}

    # Level 1
    def apply(self, op: str, row: list[str]) -> str:
        code = self._check(row[0] in self._rows, op, row)
        if code == OK:
            if op == "delete":
                del self._rows[row[0]]
            else:
                self._rows[row[0]] = list(row)
        return code

    def rows(self) -> list[list[str]]:
        return [list(self._rows[key]) for key in sorted(self._rows)]

    # Level 2
    def apply_at(self, lsn: int, op: str, row: list[str]) -> str:
        key = row[0]
        if lsn <= self._floor or lsn <= self._versions.get(key, NEVER):
            return SKIPPED
        code = self.apply(op, row)
        if code == OK:
            self._versions[key] = lsn
        return code

    def version(self, key: str) -> int:
        return self._versions.get(key, NEVER)

    # Level 3
    def load_snapshot(self, lsn: int, snapshot: list[list[str]]) -> None:
        self._rows = {row[0]: list(row) for row in snapshot}
        self._versions = dict.fromkeys(self._rows, lsn)
        self._floor = lsn

    def stage(self, tx: str, op: str, row: list[str]) -> None:
        self._staged.setdefault(tx, []).append((op, list(row)))

    def commit(self, lsn: int, tx: str) -> str:
        changes = self._staged.pop(tx, [])
        if lsn <= self._floor:
            return SKIPPED
        overlay: dict[str, list[str] | None] = {}
        for op, row in changes:
            key = row[0]
            if lsn <= self._versions.get(key, NEVER):
                continue
            present = overlay[key] is not None if key in overlay else key in self._rows
            code = self._check(present, op, row)
            if code != OK:
                return code
            overlay[key] = None if op == "delete" else list(row)
        if not overlay:
            return SKIPPED
        for key, row in overlay.items():
            if row is None:
                self._rows.pop(key, None)
            else:
                self._rows[key] = row
            self._versions[key] = lsn
        return OK

    def rollback(self, tx: str) -> None:
        self._staged.pop(tx, None)

    # Level 4
    def alter_at(self, lsn: int, change: list[str]) -> str:
        if lsn <= self._floor or lsn <= self._schema_version:
            return SKIPPED
        code = self._alter(change)
        if code == OK:
            self._schema_version = lsn
        return code

    def columns(self) -> list[str]:
        return list(self._columns)

    def compare(self, source_columns: list[str], source_rows: list[list[str]]) -> list[list[str]]:
        mine, theirs = set(self._columns), set(source_columns)
        report = [
            ["missing-column" if name in theirs else "extra-column", name]
            for name in sorted(mine ^ theirs)
        ]
        common = sorted(mine & theirs)
        source = {row[0]: row for row in source_rows}
        for key in sorted(source.keys() | self._rows.keys()):
            if key not in self._rows:
                report.append(["missing-row", key])
            elif key not in source:
                report.append(["extra-row", key])
            else:
                for name in common:
                    here = self._rows[key][self._columns.index(name)]
                    there = source[key][source_columns.index(name)]
                    if here != there:
                        report.append(["value-differs", key, name, here, there])
        return report

    # Changes
    def _check(self, present: bool, op: str, row: list[str]) -> str:
        if op != "delete" and len(row) != len(self._columns):
            return "column-count"
        if op == "insert":
            return "duplicate-key" if present else OK
        return OK if present else "unknown-key"

    def _alter(self, change: list[str]) -> str:
        kind, name = change[0], change[1]
        if kind == "add":
            if name in self._columns:
                return "duplicate-column"
            self._columns.append(name)
            for row in self._rows.values():
                row.append(change[2])
            return OK
        if name not in self._columns:
            return "unknown-column"
        index = self._columns.index(name)
        if kind == "drop":
            if index == 0:
                return "key-column"
            del self._columns[index]
            for row in self._rows.values():
                del row[index]
            return OK
        if change[2] in self._columns:
            return "duplicate-column"
        self._columns[index] = change[2]
        return OK
