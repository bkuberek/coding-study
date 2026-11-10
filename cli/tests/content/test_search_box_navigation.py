"""search-box-navigation promises that its hidden cases catch the classic mistakes of a search box:
keyup taken for the up arrow, `-1 % n`, a wrap one place late, keys that should do nothing,
regular expressions, stale responses and a list that reopens after a selection. These tests replay
every case against a model of the box written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0304-search-box-navigation"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
ARROW_DOWN = "ArrowDown"
ARROW_UP = "ArrowUp"
ENTER = "Enter"
NOTHING = -1


class Box:
    """The box as the statement words it, one rule per method, so that each mistake below
    overrides a single method. Its methods take a call's arguments without the timestamp."""

    def __init__(self, names: Sequence[str]) -> None:
        self.names = list(names)
        self.shown: list[str] = []
        self.position: int | None = None
        self.text = ""
        self.sent = 0
        self.latest: int | None = None
        self.selected: list[str] = []

    def keydown(self, key: str) -> None:
        if key == ARROW_DOWN:
            self.move_down()
        elif key == ARROW_UP:
            self.move_up()
        elif key == ENTER:
            self.select()

    def keyup(self, key: str) -> None:
        """A key coming back up changes nothing."""

    def results_arrived(self, items: Sequence[str]) -> None:
        self.show(items)

    def search(self, query: str) -> None:
        self.show([name for name in self.names if self.matches(name, query)])

    def input_changed(self, text: str) -> int:
        self.text = text
        if not text.strip():
            self.clear()
            return NOTHING
        self.sent += 1
        self.latest = self.sent
        return self.sent

    def response_arrived(self, request_id: int, items: Sequence[str]) -> None:
        if request_id == self.latest:
            self.show(items)

    def results(self) -> list[str]:
        return list(self.shown)

    def highlighted(self) -> int:
        return NOTHING if self.position is None else self.position

    def highlighted_text(self) -> str:
        return "" if self.position is None else self.shown[self.position]

    def input_text(self) -> str:
        return self.text

    def selections(self) -> list[str]:
        return list(self.selected)

    def matches(self, name: str, query: str) -> bool:
        needle = query.strip().lower()
        return needle != "" and needle in name.lower()

    def move_down(self) -> None:
        if self.position is not None:
            self.position = (self.position + 1) % len(self.shown)

    def move_up(self) -> None:
        if self.position is not None:
            self.position = (self.position - 1) % len(self.shown)

    def select(self) -> None:
        if self.position is None:
            return
        choice = self.shown[self.position]
        self.selected.append(choice)
        self.fill(choice)

    def fill(self, choice: str) -> None:
        self.text = choice
        self.forget_request()
        self.close()

    def clear(self) -> None:
        self.forget_request()
        self.close()

    def forget_request(self) -> None:
        self.latest = None

    def close(self) -> None:
        self.show([])

    def show(self, items: Sequence[str]) -> None:
        self.shown = list(items)
        self.position = 0 if self.shown else None


class KeyupMovesUp(Box):
    """Reads `keyup` as the up arrow."""

    def keyup(self, key: str) -> None:
        self.move_up()


class KeyupActsLikeKeydown(Box):
    """Listens to both events, so a press moves the highlight twice."""

    def keyup(self, key: str) -> None:
        self.keydown(key)


class PressHandledTwice(Box):
    """A global listener added twice and never removed: each press runs twice."""

    def keydown(self, key: str) -> None:
        super().keydown(key)
        super().keydown(key)


class ListenerOutlivesTheList(Box):
    """A listener added for a list and never removed keeps moving through it once it is gone."""

    def __init__(self, names: Sequence[str]) -> None:
        super().__init__(names)
        self.listened: list[str] = []

    def show(self, items: Sequence[str]) -> None:
        super().show(items)
        if self.shown:
            self.listened = self.shown

    def move_down(self) -> None:
        if self.listened:
            start = NOTHING if self.position is None else self.position
            self.position = (start + 1) % len(self.listened)


class EveryOtherKeyMovesDown(Box):
    """`if (key === "ArrowUp") up(); else down();`"""

    def keydown(self, key: str) -> None:
        if key in (ARROW_UP, ENTER):
            super().keydown(key)
        else:
            self.move_down()


class KeyNamesMatchedLoosely(Box):
    """`key.includes("Down")`, which `PageDown` passes too."""

    def keydown(self, key: str) -> None:
        if "Down" in key:
            self.move_down()
        elif "Up" in key:
            self.move_up()
        else:
            super().keydown(key)


class NegativeRemainder(Box):
    """The remainder of most languages, which keeps the sign of the dividend: `-1 % n` is -1."""

    def move_up(self) -> None:
        if self.position is not None:
            self.position = int(math.fmod(self.position - 1, len(self.shown)))


class UpWrapsOneLate(Box):
    """Wraps from the first result to position n instead of n - 1."""

    def move_up(self) -> None:
        if self.position is not None:
            self.position = self.position - 1 if self.position > 0 else len(self.shown)


class DownWrapsOneLate(Box):
    """Wraps once past position n instead of past n - 1."""

    def move_down(self) -> None:
        if self.position is not None:
            self.position = self.position + 1 if self.position < len(self.shown) else 0


class NoEmptyListGuard(Box):
    """Takes `% n` without checking that the list holds anything."""

    def move_down(self) -> None:
        start = 0 if self.position is None else self.position
        self.position = (start + 1) % len(self.shown)


class KeepsTheHighlightOnNewResults(Box):
    """Leaves the highlight where it was when a new list arrives."""

    def show(self, items: Sequence[str]) -> None:
        kept = self.position
        super().show(items)
        if kept is not None and kept < len(self.shown):
            self.position = kept


class RegularExpressionMatch(Box):
    """`new RegExp(query, "i")`: metacharacters stop being plain characters."""

    def matches(self, name: str, query: str) -> bool:
        needle = query.strip()
        return needle != "" and re.search(needle, name, re.IGNORECASE) is not None


class EmptyQueryMatchesEverything(Box):
    """Forgets that every name contains the empty string."""

    def matches(self, name: str, query: str) -> bool:
        return query.strip().lower() in name.lower()


class CaseSensitiveMatch(Box):
    """Compares the query with the names as typed."""

    def matches(self, name: str, query: str) -> bool:
        needle = query.strip()
        return needle != "" and needle in name


class UntrimmedQuery(Box):
    """Keeps the spaces at both ends of the query."""

    def matches(self, name: str, query: str) -> bool:
        needle = query.lower()
        return needle.strip() != "" and needle in name.lower()


class InnerSpacesRemoved(Box):
    """Removes every space of the query, not only those at its ends."""

    def matches(self, name: str, query: str) -> bool:
        needle = query.replace(" ", "").lower()
        return needle != "" and needle in name.lower()


class SortedMatches(Box):
    """Sorts the matches instead of keeping the order of the names."""

    def search(self, query: str) -> None:
        self.show(sorted(name for name in self.names if self.matches(name, query)))


class NewestResponseSoFarWins(Box):
    """Shows any response newer than the last one shown, instead of only the latest request's."""

    def __init__(self, names: Sequence[str]) -> None:
        super().__init__(names)
        self.newest_shown = 0

    def response_arrived(self, request_id: int, items: Sequence[str]) -> None:
        if request_id > self.newest_shown:
            self.newest_shown = request_id
            self.show(items)


class ClearKeepsTheRequest(Box):
    """Empties the list on a cleared input, but still awaits the last request."""

    def clear(self) -> None:
        self.close()


class ClearKeepsTheList(Box):
    """Forgets the request on a cleared input, but leaves the old list showing."""

    def clear(self) -> None:
        self.forget_request()


class ClearTakesAnId(Box):
    """Counts a cleared input as a request."""

    def input_changed(self, text: str) -> int:
        if not text.strip():
            self.sent += 1
        return super().input_changed(text)


class SelectsOnKeyup(Box):
    """Selects when `Enter` comes back up instead of when it goes down."""

    def keydown(self, key: str) -> None:
        if key != ENTER:
            super().keydown(key)

    def keyup(self, key: str) -> None:
        if key == ENTER:
            self.select()


class SelectionKeepsTheListOpen(Box):
    """Fills the input but leaves the list and its highlight showing."""

    def fill(self, choice: str) -> None:
        self.text = choice
        self.forget_request()


class SelectionKeepsTheRequest(Box):
    """Closes the list but still awaits the last request, whose response reopens it."""

    def fill(self, choice: str) -> None:
        self.text = choice
        self.close()


class SelectsNothingAsEmptyText(Box):
    """Reports `highlightedText()` on `Enter` even when nothing is highlighted."""

    def select(self) -> None:
        if self.position is None:
            self.selected.append("")
            return
        super().select()


MISTAKES: Sequence[type[Box]] = Box.__subclasses__()


def outputs(box_type: type[Box], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    box = box_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(box, snake_case(op))(*arguments[1:]) for op, arguments in calls)]


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def passes(box_type: type[Box], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(box_type, case) == case["expected"]
    except (IndexError, ZeroDivisionError, re.error):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Box, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__
