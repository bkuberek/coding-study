from bisect import bisect_right

OPEN_END = 99991231
UNKNOWN_MEMBER = 0


class _Version:
    __slots__ = ("key", "business_key", "values", "valid_from", "valid_to")

    def __init__(
        self, key: int, business_key: str, values: list[str], valid_from: int, valid_to: int
    ) -> None:
        self.key = key
        self.business_key = business_key
        self.values = values
        self.valid_from = valid_from
        self.valid_to = valid_to

    def row(self) -> list[str]:
        current = "Y" if self.valid_to == OPEN_END else "N"
        return [
            str(self.key),
            self.business_key,
            *self.values,
            str(self.valid_from),
            str(self.valid_to),
            current,
        ]


def _start(version: _Version) -> int:
    return version.valid_from


class DimensionTable:
    """Every business key keeps its versions in a list sorted by `valid_from`, and the versions
    never overlap, so the version valid at a date is one binary search away. Untracked attributes
    hold one value per business key, copied into every version, and the date of the latest load
    that carried the key decides whether a row may still overwrite them."""

    def __init__(self, attributes: list[str]) -> None:
        self._position = {name: index for index, name in enumerate(attributes)}
        self._tracked: list[int] = []
        self._by_surrogate: dict[int, _Version] = {}
        self._versions: dict[str, list[_Version]] = {}
        self._last_load: dict[str, int] = {}
        self._next_key = 1

    # Level 1
    def load(self, rows: list[list[str]], load_date: int) -> list[int]:
        counts, _ = self._apply(rows, load_date)
        return counts

    def lookup(self, business_key: str) -> int:
        versions = self._versions.get(business_key)
        if versions is None or versions[-1].valid_to != OPEN_END:
            return -1
        return versions[-1].key

    def row_of(self, surrogate_key: int) -> list[str]:
        version = self._by_surrogate.get(surrogate_key)
        return version.row() if version is not None else []

    def size(self) -> int:
        return len(self._by_surrogate)

    # Level 2
    def track_history(self, attribute: str) -> bool:
        index = self._position.get(attribute)
        if index is None or index in self._tracked:
            return False
        self._tracked.append(index)
        return True

    def history(self, business_key: str) -> list[list[str]]:
        return [version.row() for version in self._versions.get(business_key, [])]

    # Level 3
    def lookup_at(self, business_key: str, as_of: int) -> int:
        version = self._valid_at(business_key, as_of)
        return version.key if version is not None else -1

    def snapshot_at(self, as_of: int) -> list[list[str]]:
        rows = []
        for business_key in sorted(self._versions):
            version = self._valid_at(business_key, as_of)
            if version is not None:
                rows.append(version.row())
        return rows

    def resolve_facts(self, facts: list[list[str]]) -> list[list[str]]:
        resolved = []
        for fact_id, business_key, event_date in facts:
            if business_key not in self._versions:
                resolved.append([fact_id, str(UNKNOWN_MEMBER), "unknown-key"])
                continue
            version = self._valid_at(business_key, int(event_date))
            if version is None:
                resolved.append([fact_id, str(UNKNOWN_MEMBER), "no-version"])
            elif version.valid_to == OPEN_END:
                resolved.append([fact_id, str(version.key), "current"])
            else:
                resolved.append([fact_id, str(version.key), "late"])
        return resolved

    # Level 4
    def load_full(self, rows: list[list[str]], load_date: int) -> list[int]:
        counts, present = self._apply(rows, load_date)
        closed = 0
        for business_key in sorted(self._versions):
            last = self._versions[business_key][-1]
            if business_key not in present and last.valid_to == OPEN_END:
                last.valid_to = load_date
                closed += 1
        return [*counts, closed]

    def full_history(self) -> list[list[str]]:
        return [
            version.row()
            for business_key in sorted(self._versions)
            for version in self._versions[business_key]
        ]

    # Helpers
    def _apply(self, rows: list[list[str]], load_date: int) -> tuple[list[int], set[str]]:
        latest = {row[0]: row[1:] for row in rows}
        inserted = changed = unchanged = 0
        for business_key in sorted(latest):
            values = latest[business_key]
            if business_key not in self._versions:
                self._versions[business_key] = []
                self._last_load[business_key] = load_date
                self._insert(business_key, list(values), load_date, OPEN_END)
                inserted += 1
            elif self._merge(business_key, values, load_date):
                changed += 1
            else:
                unchanged += 1
        return [inserted, changed, unchanged], set(latest)

    def _merge(self, business_key: str, values: list[str], load_date: int) -> bool:
        versions = self._versions[business_key]
        changed = False
        if load_date >= self._last_load[business_key]:
            self._last_load[business_key] = load_date
            for index in self._untracked():
                if versions[0].values[index] != values[index]:
                    for version in versions:
                        version.values[index] = values[index]
                    changed = True
        holder = self._valid_at(business_key, load_date)
        if holder is not None:
            if all(holder.values[index] == values[index] for index in self._tracked):
                return changed
            if holder.valid_from == load_date:
                for index in self._tracked:
                    holder.values[index] = values[index]
                return True
            fresh = self._combine(versions[0], values)
            end = holder.valid_to
            holder.valid_to = load_date
            self._insert(business_key, fresh, load_date, end)
            return True
        after = [v.valid_from for v in versions if v.valid_from > load_date]
        end = after[0] if after else OPEN_END
        self._insert(business_key, self._combine(versions[0], values), load_date, end)
        return True

    def _combine(self, shared: _Version, values: list[str]) -> list[str]:
        """The incoming tracked values with the key's untracked values."""
        combined = list(shared.values)
        for index in self._tracked:
            combined[index] = values[index]
        return combined

    def _untracked(self) -> list[int]:
        return [index for index in self._position.values() if index not in self._tracked]

    def _insert(self, business_key: str, values: list[str], valid_from: int, valid_to: int) -> None:
        version = _Version(self._next_key, business_key, values, valid_from, valid_to)
        self._next_key += 1
        self._by_surrogate[version.key] = version
        versions = self._versions[business_key]
        at = bisect_right(versions, valid_from, key=_start)
        versions.insert(at, version)

    def _valid_at(self, business_key: str, as_of: int) -> _Version | None:
        versions = self._versions.get(business_key)
        if not versions:
            return None
        at = bisect_right(versions, as_of, key=_start) - 1
        if at < 0 or as_of >= versions[at].valid_to:
            return None
        return versions[at]
