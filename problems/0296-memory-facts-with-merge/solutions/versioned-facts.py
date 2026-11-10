from bisect import bisect_right
from dataclasses import dataclass

REFERENCE_MARK = "@"

Key = tuple[str, str]
"""A subject and an attribute: the name of a fact within one user."""


def _fact_id(number: int) -> str:
    return f"f{number}"


@dataclass(frozen=True, slots=True)
class _Fact:
    """One version of a fact: its number in this store, the time it was remembered, its value."""

    number: int
    time: int
    value: str

    @property
    def fact_id(self) -> str:
        return _fact_id(self.number)


class _History:
    """Every version of one subject and attribute, oldest first; times never decrease."""

    def __init__(self) -> None:
        self._facts: list[_Fact] = []

    def add(self, fact: _Fact) -> None:
        self._facts.append(fact)

    @property
    def current(self) -> _Fact:
        return self._facts[-1]

    @property
    def facts(self) -> list[_Fact]:
        return list(self._facts)

    def in_force_at(self, moment: int) -> _Fact | None:
        position = bisect_right(self._facts, moment, key=lambda fact: fact.time)
        return self._facts[position - 1] if position else None


def _replaces(incoming: _Fact, held: _History | None, incoming_wins_ties: bool) -> bool:
    if held is None:
        return True
    if incoming.time != held.current.time:
        return incoming.time > held.current.time
    return incoming_wins_ties


def _follow(value: str, new_ids: dict[str, str]) -> str:
    """The value with a reference to an imported id pointed at that fact's new id."""
    if value.startswith(REFERENCE_MARK) and value[1:] in new_ids:
        return REFERENCE_MARK + new_ids[value[1:]]
    return value


class FactMemory:
    def __init__(self) -> None:
        self._users: dict[str, dict[Key, _History]] = {}
        self._priorities: dict[str, int] = {}
        self._last_number = 0

    # Level 1
    def remember(self, timestamp: int, user: str, subject: str, attribute: str, value: str) -> str:
        return self._add(user, (subject, attribute), timestamp, value).fact_id

    def recall(self, timestamp: int, user: str, subject: str, attribute: str) -> str:
        history = self._history(user, (subject, attribute))
        return history.current.value if history else ""

    def list_facts(self, timestamp: int, user: str) -> list[str]:
        facts = self._users.get(user, {})
        return [
            f"{subject}.{attribute}={facts[subject, attribute].current.value}"
            for subject, attribute in sorted(facts)
        ]

    # Level 2
    def recall_at(self, timestamp: int, user: str, subject: str, attribute: str, at: int) -> str:
        history = self._history(user, (subject, attribute))
        fact = history.in_force_at(at) if history else None
        return fact.value if fact else ""

    def history(self, timestamp: int, user: str, subject: str, attribute: str) -> list[str]:
        history = self._history(user, (subject, attribute))
        facts = history.facts if history else []
        return [f"{fact.fact_id}@{fact.time}={fact.value}" for fact in facts]

    # Level 3
    def set_priority(self, timestamp: int, user: str, priority: int) -> None:
        self._priorities[user] = priority

    def merge(self, timestamp: int, from_user: str, into_user: str) -> int:
        incoming = self._users.get(from_user, {})
        held = self._users.get(into_user, {})
        incoming_wins_ties = self._priority(from_user) > self._priority(into_user)
        taken = [
            (key, incoming[key].current)
            for key in sorted(incoming)
            if _replaces(incoming[key].current, held.get(key), incoming_wins_ties)
        ]
        for key, fact in taken:
            self._add(into_user, key, fact.time, fact.value)
        return len(taken)

    # Level 4
    def export_facts(self, timestamp: int, user: str) -> list[str]:
        versions = [
            (fact, subject, attribute)
            for (subject, attribute), history in self._users.get(user, {}).items()
            for fact in history.facts
        ]
        versions.sort(key=lambda version: version[0].number)
        return [
            f"{fact.fact_id} {fact.time} {subject} {attribute} {fact.value}"
            for fact, subject, attribute in versions
        ]

    def import_facts(self, timestamp: int, user: str, lines: list[str]) -> list[str]:
        if self._users.get(user):
            return []
        rows = [line.split(" ") for line in lines]
        # Every new number is given out before any value is rewritten, so a reference may
        # name a line further down.
        new_numbers = {old_id: self._next_number() for old_id, *_ in rows}
        new_ids = {old_id: _fact_id(number) for old_id, number in new_numbers.items()}
        for old_id, time, subject, attribute, value in rows:
            fact = _Fact(new_numbers[old_id], int(time), _follow(value, new_ids))
            self._store(user, (subject, attribute), fact)
        return [new_ids[old_id] for old_id, *_ in rows]

    def _add(self, user: str, key: Key, time: int, value: str) -> _Fact:
        fact = _Fact(self._next_number(), time, value)
        self._store(user, key, fact)
        return fact

    def _store(self, user: str, key: Key, fact: _Fact) -> None:
        self._users.setdefault(user, {}).setdefault(key, _History()).add(fact)

    def _next_number(self) -> int:
        self._last_number += 1
        return self._last_number

    def _history(self, user: str, key: Key) -> _History | None:
        return self._users.get(user, {}).get(key)

    def _priority(self, user: str) -> int:
        return self._priorities.get(user, 0)
