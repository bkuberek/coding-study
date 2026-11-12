from collections import defaultdict


class StreamWindows:
    """Every event is kept in a log, so the batch views of levels 1 and 2 can group the whole
    stream in any way they are asked.

    The stream of levels 3 and 4 keeps a map from (start, key) to a running [count, sum] for the
    windows not yet emitted, and a second map for the windows already emitted that can still be
    corrected. After each event the watermark moves, the open windows it has passed are emitted
    in order, and the corrected windows it has left behind are forgotten.
    """

    def __init__(self) -> None:
        self._events: list[tuple[int, int, int]] = []
        self._size = 0
        self._lateness = 0
        self._grace = 0
        self._mark = 0
        self._open: dict[tuple[int, int], list[int]] = {}
        self._closed: dict[tuple[int, int], list[int]] = {}
        self._out: list[list[int]] = []
        self._side: list[list[int]] = []
        self._emitted = 0
        self._updated = 0

    # Level 1
    def add(self, key: int, time: int, value: int) -> None:
        self._events.append((key, time, value))
        if self._size > 0:
            self._stream(key, time, value)

    def tumbling(self, size: int) -> list[list[int]]:
        groups: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
        for key, time, value in self._events:
            group = groups[(time - time % size, key)]
            group[0] += 1
            group[1] += value
        return [[key, start, start + size, c, s] for (start, key), (c, s) in sorted(groups.items())]

    # Level 2
    def hopping(self, size: int, slide: int) -> list[list[int]]:
        groups: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
        for key, time, value in self._events:
            start = time - time % slide
            while start > time - size:
                group = groups[(start, key)]
                group[0] += 1
                group[1] += value
                start -= slide
        return [[key, start, start + size, c, s] for (start, key), (c, s) in sorted(groups.items())]

    def sessions(self, gap: int) -> list[list[int]]:
        by_key: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for key, time, value in self._events:
            by_key[key].append((time, value))
        rows = []
        for key, events in by_key.items():
            events.sort()
            row: list[int] = []
            for time, value in events:
                if row and time < row[2]:
                    row[2] = time + gap
                    row[3] += 1
                    row[4] += value
                else:
                    row = [key, time, time + gap, 1, value]
                    rows.append(row)
        return sorted(rows, key=lambda row: (row[1], row[0]))

    # Level 3
    def configure(self, size: int, lateness: int) -> None:
        self._size = size
        self._lateness = lateness

    def watermark(self) -> int:
        return self._mark

    def pending(self) -> list[list[int]]:
        return [self._row(window, totals) for window, totals in sorted(self._open.items())]

    def poll(self) -> list[list[int]]:
        out, self._out = self._out, []
        return out

    # Level 4
    def allow_updates(self, grace: int) -> None:
        self._grace = grace

    def dropped(self) -> list[list[int]]:
        return [list(event) for event in self._side]

    def stats(self) -> list[int]:
        return [self._emitted, self._updated, len(self._side)]

    # The stream
    def _row(self, window: tuple[int, int], totals: list[int]) -> list[int]:
        start, key = window
        return [key, start, start + self._size, totals[0], totals[1]]

    def _stream(self, key: int, time: int, value: int) -> None:
        start = time - time % self._size
        window = (start, key)
        end = start + self._size
        if end > self._mark:
            totals = self._open.setdefault(window, [0, 0])
            totals[0] += 1
            totals[1] += value
        elif self._mark < end + self._grace:
            self._correct(window, value)
        else:
            self._side.append([key, time, value])
        self._advance(time - self._lateness)

    def _correct(self, window: tuple[int, int], value: int) -> None:
        old = self._closed.get(window)
        if old is None:
            self._closed[window] = [1, value]
            self._emitted += 1
        else:
            self._out.append(self._row(window, [-old[0], -old[1]]))
            self._closed[window] = [old[0] + 1, old[1] + value]
            self._updated += 1
        self._out.append(self._row(window, self._closed[window]))

    def _advance(self, candidate: int) -> None:
        if candidate <= self._mark:
            return
        self._mark = candidate
        due = sorted(w for w in self._open if w[0] + self._size <= self._mark)
        for window in due:
            totals = self._open.pop(window)
            self._out.append(self._row(window, totals))
            self._closed[window] = totals
            self._emitted += 1
        for window in [w for w in self._closed if w[0] + self._size + self._grace <= self._mark]:
            del self._closed[window]
