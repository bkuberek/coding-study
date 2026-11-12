from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Stamp:
    """Everything one event carries: where it ran, its three clocks and, for a write, the write."""

    process: int
    lamport: int
    vector: tuple[int, ...]
    hybrid: tuple[int, int]
    wall: int
    is_send: bool
    key: str = ""
    value: str = ""


def at_most(first: tuple[int, ...], second: tuple[int, ...]) -> bool:
    return all(a <= b for a, b in zip(first, second, strict=True))


class LogicalClocks:
    """Each process keeps the current value of its three clocks: a Lamport counter, a vector and a
    hybrid pair. Every event updates them by the rules of its kind and keeps a copy as its stamp,
    so every question afterwards is answered from the stamps alone."""

    def __init__(self, processes: int) -> None:
        self._processes = processes
        self._lamport = [0] * processes
        self._vector = [tuple([0] * processes) for _ in range(processes)]
        self._hybrid = [(0, 0)] * processes
        self._events: dict[str, Stamp] = {}
        self._received: set[str] = set()
        self._writes: dict[str, list[str]] = {}

    # Level 1
    def local(self, process: int, event: str, wall: int) -> int:
        return self._record(process, event, wall, None, False)

    def send(self, process: int, event: str, wall: int) -> int:
        return self._record(process, event, wall, None, True)

    def receive(self, process: int, event: str, message: str, wall: int) -> int:
        sent = self._events.get(message)
        if sent is None or not sent.is_send or message in self._received:
            return -1
        if sent.process == process:
            return -1
        stamp = self._record(process, event, wall, sent, False)
        if stamp != -1:
            self._received.add(message)
        return stamp

    def total_order(self) -> list[str]:
        return sorted(self._events, key=lambda name: self._order_key(name, "lamport"))

    # Level 2
    def vector(self, event: str) -> list[int]:
        stamp = self._events.get(event)
        return list(stamp.vector) if stamp else []

    def compare(self, first: str, second: str) -> str:
        if first not in self._events or second not in self._events:
            return ""
        if first == second:
            return "same"
        one, other = self._events[first].vector, self._events[second].vector
        if at_most(one, other):
            return "before"
        if at_most(other, one):
            return "after"
        return "concurrent"

    # Level 3
    def write(self, process: int, event: str, key: str, value: str, wall: int) -> int:
        stamp = self._record(process, event, wall, None, False)
        if stamp != -1:
            self._events[event] = replace(self._events[event], key=key, value=value)
            self._writes.setdefault(key, []).append(event)
        return stamp

    def read(self, process: int, key: str) -> list[str]:
        if not 0 <= process < self._processes:
            return []
        now = self._vector[process]
        known = [self._events[name] for name in self._writes.get(key, [])]
        known = [stamp for stamp in known if at_most(stamp.vector, now)]
        siblings = [
            stamp
            for stamp in known
            if not any(other is not stamp and at_most(stamp.vector, other.vector) for other in known)
        ]
        return sorted(stamp.value for stamp in siblings)

    def concurrent_writes(self, key: str) -> list[list[str]]:
        names = sorted(self._writes.get(key, []))
        pairs = []
        for index, first in enumerate(names):
            for second in names[index + 1 :]:
                if self.compare(first, second) == "concurrent":
                    pairs.append([first, second])
        return pairs

    # Level 4
    def hlc(self, event: str) -> list[int]:
        stamp = self._events.get(event)
        return list(stamp.hybrid) if stamp else []

    def hlc_order(self) -> list[str]:
        return sorted(self._events, key=lambda name: self._order_key(name, "hybrid"))

    def max_offset(self) -> int:
        return max((stamp.hybrid[0] - stamp.wall for stamp in self._events.values()), default=0)

    # Shared
    def _order_key(self, name: str, clock: str) -> tuple:
        stamp = self._events[name]
        if clock == "lamport":
            return (stamp.lamport, stamp.process)
        return (*stamp.hybrid, stamp.process)

    def _record(self, process: int, event: str, wall: int, sent: Stamp | None, is_send: bool) -> int:
        if not 0 <= process < self._processes or event in self._events:
            return -1
        lamport = self._lamport[process]
        vector = list(self._vector[process])
        if sent is None:
            lamport += 1
        else:
            lamport = max(lamport, sent.lamport) + 1
            vector = [max(mine, theirs) for mine, theirs in zip(vector, sent.vector, strict=True)]
        vector[process] += 1
        hybrid = self._next_hybrid(self._hybrid[process], wall, sent)
        self._lamport[process] = lamport
        self._vector[process] = tuple(vector)
        self._hybrid[process] = hybrid
        self._events[event] = Stamp(process, lamport, tuple(vector), hybrid, wall, is_send)
        return lamport

    @staticmethod
    def _next_hybrid(current: tuple[int, int], wall: int, sent: Stamp | None) -> tuple[int, int]:
        """The update of Kulkarni et al.: `l` is the largest physical reading heard of, and `c`
        counts the events since `l` last changed."""
        old_l, old_c = current
        if sent is None:
            new_l = max(old_l, wall)
            return (new_l, old_c + 1 if new_l == old_l else 0)
        sent_l, sent_c = sent.hybrid
        new_l = max(old_l, sent_l, wall)
        if new_l == old_l == sent_l:
            return (new_l, max(old_c, sent_c) + 1)
        if new_l == old_l:
            return (new_l, old_c + 1)
        if new_l == sent_l:
            return (new_l, sent_c + 1)
        return (new_l, 0)
