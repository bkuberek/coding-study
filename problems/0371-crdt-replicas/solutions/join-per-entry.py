from dataclasses import dataclass


@dataclass
class Slot:
    """One replica's slot of a counter: what it added (`up`) and what it took away (`down`), each
    with the change number at which it last grew."""

    up: int = 0
    up_at: int = 0
    down: int = 0
    down_at: int = 0


@dataclass
class Register:
    text: str
    timestamp: int
    writer: str
    at: int

    def stamp(self) -> tuple[int, str]:
        return (self.timestamp, self.writer)


@dataclass
class Tag:
    added_at: int
    removed: bool = False
    removed_at: int = 0


class Replica:
    """The whole state of one replica. Every entry (a counter slot's up or down part, a register,
    an add tag, a tombstone) only grows, and each one remembers the change number at which it last
    grew, so a sync can pick the entries that changed after the last acknowledgement."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.clock = 0
        self.adds = 0
        self.counters: dict[str, dict[str, Slot]] = {}
        self.registers: dict[str, Register] = {}
        self.sets: dict[str, dict[str, dict[str, Tag]]] = {}
        self.acked: dict[str, int] = {}

    def tick(self) -> int:
        self.clock += 1
        return self.clock

    def slot(self, counter: str, owner: str) -> Slot:
        return self.counters.setdefault(counter, {}).setdefault(owner, Slot())

    def total(self, counter: str) -> int:
        slots = self.counters.get(counter, {}).values()
        return sum(slot.up - slot.down for slot in slots)

    def tags(self, set_name: str, element: str) -> dict[str, Tag]:
        return self.sets.setdefault(set_name, {}).setdefault(element, {})

    def live(self, set_name: str, element: str) -> bool:
        tags = self.sets.get(set_name, {}).get(element, {})
        return any(not tag.removed for tag in tags.values())

    def size(self) -> int:
        slots = [slot for counter in self.counters.values() for slot in counter.values()]
        parts = sum((slot.up > 0) + (slot.down > 0) for slot in slots)
        tags = [tag for elements in self.sets.values() for t in elements.values() for tag in t.values()]
        return parts + len(self.registers) + sum(1 + tag.removed for tag in tags)

    def absorb(self, source: "Replica", since: int) -> int:
        """Joins every entry of `source` that changed after `since` into this replica and returns
        how many entries that was. `since = 0` is a full-state merge."""
        sent = 0
        for counter, slots in source.counters.items():
            for owner, theirs in slots.items():
                mine = self.slot(counter, owner)
                if theirs.up > 0 and theirs.up_at > since:
                    sent += 1
                    if theirs.up > mine.up:
                        mine.up, mine.up_at = theirs.up, self.tick()
                if theirs.down > 0 and theirs.down_at > since:
                    sent += 1
                    if theirs.down > mine.down:
                        mine.down, mine.down_at = theirs.down, self.tick()
        for name, theirs in source.registers.items():
            if theirs.at > since:
                sent += 1
                mine = self.registers.get(name)
                if mine is None or theirs.stamp() > mine.stamp():
                    self.registers[name] = Register(
                        theirs.text, theirs.timestamp, theirs.writer, self.tick()
                    )
        for set_name, elements in source.sets.items():
            for element, tags in elements.items():
                for tag, theirs in tags.items():
                    sent += self.absorb_tag(self.tags(set_name, element), tag, theirs, since)
        return sent

    def absorb_tag(self, mine: dict[str, Tag], tag: str, theirs: Tag, since: int) -> int:
        sent = 0
        if theirs.added_at > since:
            sent += 1
            if tag not in mine:
                mine[tag] = Tag(self.tick())
        if theirs.removed and theirs.removed_at > since:
            sent += 1
            if tag not in mine:
                mine[tag] = Tag(self.tick())
            if not mine[tag].removed:
                mine[tag].removed, mine[tag].removed_at = True, self.tick()
        return sent


class Replicas:
    """A group of replicas of the same data. Each replica's state is a set of entries that only
    grow, and merging is taking the larger value of every entry, so merges can happen in any order,
    any number of times, and replicas that have seen the same updates hold the same state."""

    def __init__(self, ids: list[str]) -> None:
        self._replicas = {name: Replica(name) for name in ids}

    # Level 1
    def increment(self, replica: str, counter: str, amount: int) -> int:
        node = self._replicas[replica]
        slot = node.slot(counter, replica)
        slot.up, slot.up_at = slot.up + amount, node.tick()
        return node.total(counter)

    def decrement(self, replica: str, counter: str, amount: int) -> int:
        node = self._replicas[replica]
        slot = node.slot(counter, replica)
        slot.down, slot.down_at = slot.down + amount, node.tick()
        return node.total(counter)

    def value(self, replica: str, counter: str) -> int:
        return self._replicas[replica].total(counter)

    def merge(self, source: str, target: str) -> None:
        self._replicas[target].absorb(self._replicas[source], 0)

    # Level 2
    def write(self, replica: str, register: str, text: str, timestamp: int) -> bool:
        node = self._replicas[replica]
        current = node.registers.get(register)
        if current is not None and (timestamp, replica) <= current.stamp():
            return False
        node.registers[register] = Register(text, timestamp, replica, node.tick())
        return True

    def read(self, replica: str, register: str) -> str:
        current = self._replicas[replica].registers.get(register)
        return "" if current is None else current.text

    # Level 3
    def add(self, replica: str, set_name: str, element: str) -> str:
        node = self._replicas[replica]
        node.adds += 1
        tag = f"{replica}:{node.adds}"
        node.tags(set_name, element)[tag] = Tag(node.tick())
        return tag

    def remove(self, replica: str, set_name: str, element: str) -> int:
        node = self._replicas[replica]
        seen = [tag for tag in node.sets.get(set_name, {}).get(element, {}).values() if not tag.removed]
        for tag in seen:
            tag.removed, tag.removed_at = True, node.tick()
        return len(seen)

    def contains(self, replica: str, set_name: str, element: str) -> bool:
        return self._replicas[replica].live(set_name, element)

    def elements(self, replica: str, set_name: str) -> list[str]:
        node = self._replicas[replica]
        return sorted(e for e in node.sets.get(set_name, {}) if node.live(set_name, e))

    # Level 4
    def sync(self, source: str, target: str) -> int:
        sender, receiver = self._replicas[source], self._replicas[target]
        sent = receiver.absorb(sender, sender.acked.get(target, 0))
        sender.acked[target] = sender.clock
        return sent

    def state_size(self, replica: str) -> int:
        return self._replicas[replica].size()
