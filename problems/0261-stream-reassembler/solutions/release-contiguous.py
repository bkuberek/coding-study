class StreamReassembler:
    def __init__(self) -> None:
        # released[i] is fragment i, so the next sequence to release is len(released).
        self._released: list[str] = []
        self._held: dict[int, str] = {}
        self._highest_arrived = -1
        self._last_sequence: int | None = None
        self._closed = False

    def delta(self, sequence: int, fragment: str) -> str:
        if self._closed or self._is_past_the_end(sequence) or self._has_arrived(sequence):
            return ""
        self._held[sequence] = fragment
        self._highest_arrived = max(self._highest_arrived, sequence)
        newly_released = []
        while len(self._released) in self._held:
            piece = self._held.pop(len(self._released))
            self._released.append(piece)
            newly_released.append(piece)
        return "".join(newly_released)

    def finish(self, last_sequence: int) -> bool:
        if self._closed or self._last_sequence is not None:
            return False
        if last_sequence < self._highest_arrived:
            return False
        self._last_sequence = last_sequence
        return True

    def close(self) -> None:
        self._closed = True

    def status(self) -> str:
        if self._last_sequence is not None and len(self._released) == self._last_sequence + 1:
            return "complete"
        return "truncated" if self._closed else "streaming"

    def text(self) -> str:
        return "".join(self._released)

    def missing(self) -> list[int]:
        end = self._highest_arrived if self._last_sequence is None else self._last_sequence
        return [
            sequence
            for sequence in range(len(self._released), end + 1)
            if sequence not in self._held
        ]

    def _is_past_the_end(self, sequence: int) -> bool:
        return self._last_sequence is not None and sequence > self._last_sequence

    def _has_arrived(self, sequence: int) -> bool:
        return sequence < len(self._released) or sequence in self._held
