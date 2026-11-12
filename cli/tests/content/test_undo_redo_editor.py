"""undo-redo-editor promises that its hidden cases catch the classic mistakes of an undo history:
a redo list that survives a new edit, steps recorded for edits that change nothing, positions not
clamped, typing grouped by the wrong rule or across calls that should end the group, a restore that
cannot be undone or always records a step, and a history tree whose redo or jump forgets the branch
you were on. These tests replay every case against a model of the editor written from the statement,
which keeps a full copy of the text in every state instead of commands, and against that model with
one mistake planted at a time, which some hidden case must fail."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0366-undo-redo-editor"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
GAP_MS = 1000


class Model:
    """Every state is a full copy of the text; undo, redo and jump only move between states."""

    def __init__(self, initial: str) -> None:
        self.texts = [initial]
        self.parents: list[int | None] = [None]
        self.kids: list[list[int]] = [[]]
        self.preferred: list[int | None] = [None]
        self.at = 0
        self.saved: dict[str, str] = {}
        self.typing: tuple[int, int, str] | None = None  # group end, last time, last character

    # --- helpers that the mistakes override
    def close_group(self) -> None:
        self.typing = None

    def changes(self, new_text: str) -> bool:
        return new_text != self.current()

    def current(self) -> str:
        return self.texts[self.at]

    def add_state(self, new_text: str) -> None:
        if self.changes(new_text):
            self.new_state(new_text)

    def new_state(self, new_text: str) -> None:
        number = len(self.texts)
        self.texts.append(new_text)
        self.parents.append(self.at)
        self.kids.append([])
        self.preferred.append(None)
        self.kids[self.at].append(number)
        self.preferred[self.at] = number
        self.at = number

    def clamp(self, position: int) -> int:
        return min(position, len(self.current()))

    def joins(self, timestamp: int, position: int) -> bool:
        if self.typing is None:
            return False
        end, last, last_char = self.typing
        return position == end and timestamp - last <= GAP_MS and last_char != " "

    def follow(self, state: int) -> None:
        """Makes every state above `state` prefer the child on the way to it."""
        child, parent = state, self.parents[state]
        while parent is not None:
            self.preferred[parent] = child
            child, parent = parent, self.parents[parent]

    def valid_state(self, state: int) -> bool:
        return 0 <= state < len(self.texts)

    # --- level 1
    def text(self) -> str:
        return self.current()

    def insert(self, position: int, text: str) -> None:
        self.close_group()
        at = self.clamp(position)
        self.add_state(self.current()[:at] + text + self.current()[at:])

    def erase(self, position: int, count: int) -> None:
        self.close_group()
        at = self.clamp(position)
        self.add_state(self.current()[:at] + self.current()[at + count :])

    def undo(self) -> bool:
        self.close_group()
        parent = self.parents[self.at]
        if parent is None:
            return False
        self.at = parent
        return True

    def redo(self) -> bool:
        self.close_group()
        child = self.preferred[self.at]
        if child is None:
            return False
        self.at = child
        return True

    # --- level 2
    def type_text(self, timestamp: int, position: int, text: str) -> None:
        at = self.clamp(position)
        typed = self.current()[:at] + text + self.current()[at:]
        if self.joins(timestamp, at):
            self.texts[self.at] = typed
        else:
            self.add_state(typed)
        self.typing = (at + len(text), timestamp, text[-1])

    # --- level 3
    def checkpoint(self, name: str) -> None:
        self.close_group()
        self.saved[name] = self.current()

    def restore(self, name: str) -> bool:
        self.close_group()
        if name not in self.saved:
            return False
        self.add_state(self.saved[name])
        return True

    # --- level 4
    def state(self) -> int:
        return self.at

    def branches(self) -> list[int]:
        return list(self.kids[self.at])

    def jump(self, state: int) -> bool:
        self.close_group()
        if not self.valid_state(state):
            return False
        self.follow(state)
        self.at = state
        return True


# ------------------------------------------------------------------ level 1 mistakes
class RedoListSurvivesNewEdits(Model):
    """Keeps undone states on a redo list that only redo empties."""

    def __init__(self, initial: str) -> None:
        super().__init__(initial)
        self.undone: list[int] = []

    def undo(self) -> bool:
        here = self.at
        done = super().undo()
        if done:
            self.undone.append(here)
        return done

    def redo(self) -> bool:
        self.close_group()
        if not self.undone:
            return False
        self.at = self.undone.pop()
        return True


class EditsThatChangeNothingAreRecorded(Model):
    """Records a step for an empty insert, an empty erase and a restore to the same text."""

    def changes(self, new_text: str) -> bool:
        return True


class InsertPastTheEndIsIgnored(Model):
    """Does nothing for a position past the end instead of inserting at the end."""

    def insert(self, position: int, text: str) -> None:
        if position <= len(self.current()):
            super().insert(position, text)


class EraseCountsBackFromTheEnd(Model):
    """Erases the last `count` characters when the position is past the end."""

    def erase(self, position: int, count: int) -> None:
        if position > len(self.current()):
            position = max(0, len(self.current()) - count)
        super().erase(position, count)


class UndoAtTheStartSaysTrue(Model):
    """Answers true when there is nothing to undo."""

    def undo(self) -> bool:
        super().undo()
        return True


class RedoWithNothingSaysTrue(Model):
    """Answers true when there is nothing to redo."""

    def redo(self) -> bool:
        super().redo()
        return True


# ------------------------------------------------------------------ level 2 mistakes
class PauseOfExactlyTheGapSplits(Model):
    """Starts a new group after a pause of exactly 1000 ms."""

    def joins(self, timestamp: int, position: int) -> bool:
        typing = self.typing
        return (
            super().joins(timestamp, position)
            and typing is not None
            and timestamp - typing[1] < GAP_MS
        )


class PauseCountedFromTheGroupStart(Model):
    """Measures the pause from the first call of the group, not from the previous one."""

    def __init__(self, initial: str) -> None:
        super().__init__(initial)
        self.group_started = 0

    def type_text(self, timestamp: int, position: int, text: str) -> None:
        starts_a_group = not self.joins(timestamp, self.clamp(position))
        super().type_text(timestamp, position, text)
        if starts_a_group:
            self.group_started = timestamp

    def joins(self, timestamp: int, position: int) -> bool:
        return super().joins(timestamp, position) and timestamp - self.group_started <= GAP_MS


class AnyPositionContinuesTheGroup(Model):
    """Joins the group wherever the typing happens."""

    def joins(self, timestamp: int, position: int) -> bool:
        if self.typing is None:
            return False
        _, last, last_char = self.typing
        return timestamp - last <= GAP_MS and last_char != " "


class SpaceStartsTheNextGroup(Model):
    """Splits before a typed space instead of after it."""

    def type_text(self, timestamp: int, position: int, text: str) -> None:
        if self.typing is not None and text.startswith(" "):
            self.close_group()
        super().type_text(timestamp, position, text)

    def joins(self, timestamp: int, position: int) -> bool:
        if self.typing is None:
            return False
        end, last, _ = self.typing
        return position == end and timestamp - last <= GAP_MS


class ReadingTheTextEndsTheGroup(Model):
    """Ends the group when the text is read."""

    def text(self) -> str:
        self.close_group()
        return super().text()


class UndoAndRedoKeepTheGroup(Model):
    """Lets typing continue a group across undo and redo."""

    def undo(self) -> bool:
        typing = self.typing
        done = super().undo()
        self.typing = typing
        return done

    def redo(self) -> bool:
        typing = self.typing
        done = super().redo()
        self.typing = typing
        return done


class EditsThatChangeNothingKeepTheGroup(Model):
    """Ends the group only for an insert or an erase that changes the text."""

    def insert(self, position: int, text: str) -> None:
        if text:
            super().insert(position, text)

    def erase(self, position: int, count: int) -> None:
        if self.clamp(position) < len(self.current()) and count > 0:
            super().erase(position, count)


# ------------------------------------------------------------------ level 3 mistakes
class RestoreCannotBeUndone(Model):
    """Puts the saved text back and forgets the history."""

    def restore(self, name: str) -> bool:
        self.close_group()
        if name not in self.saved:
            return False
        if self.changes(self.saved[name]):
            no_parent: list[int | None] = [None]
            no_child: list[int | None] = [None]
            self.texts, self.parents, self.kids = [self.saved[name]], no_parent, [[]]
            self.preferred, self.at = no_child, 0
        return True


class RestoreToTheSameTextIsRecorded(Model):
    """Records a step for a restore that leaves the text as it is."""

    restoring = False

    def restore(self, name: str) -> bool:
        self.restoring = True
        try:
            return super().restore(name)
        finally:
            self.restoring = False

    def changes(self, new_text: str) -> bool:
        return self.restoring or super().changes(new_text)


class CheckpointKeepsTheGroup(Model):
    """Lets typing continue a group across a checkpoint."""

    def checkpoint(self, name: str) -> None:
        self.saved[name] = self.current()


class CheckpointKeepsTheFirstText(Model):
    """Ignores a checkpoint whose name is taken."""

    def checkpoint(self, name: str) -> None:
        self.close_group()
        self.saved.setdefault(name, self.current())


class UnknownRestoreClearsRedo(Model):
    """Records a step for a name that was never saved."""

    def restore(self, name: str) -> bool:
        if name not in self.saved:
            self.close_group()
            self.preferred[self.at] = None
            return False
        return super().restore(name)


# ------------------------------------------------------------------ level 4 mistakes
class RedoTakesTheFirstBranch(Model):
    """Redoes into the oldest child."""

    def redo(self) -> bool:
        self.close_group()
        if not self.kids[self.at]:
            return False
        self.at = self.kids[self.at][0]
        return True


class RedoTakesTheNewestBranch(Model):
    """Redoes into the newest child, whatever was visited last."""

    def redo(self) -> bool:
        self.close_group()
        if not self.kids[self.at]:
            return False
        self.at = self.kids[self.at][-1]
        return True


class JumpSetsOnlyTheParent(Model):
    """Points only the target's parent at the target."""

    def follow(self, state: int) -> None:
        parent = self.parents[state]
        if parent is not None:
            self.preferred[parent] = state


class JumpLeavesTheBranchesAlone(Model):
    """Moves to the state without telling redo which branch it is on."""

    def follow(self, state: int) -> None:
        return None


class GrowingGroupGetsANewNumber(Model):
    """Gives every call of a typing group a state of its own."""

    def type_text(self, timestamp: int, position: int, text: str) -> None:
        if self.joins(timestamp, self.clamp(position)):
            at = self.clamp(position)
            self.new_state(self.current()[:at] + text + self.current()[at:])
            self.typing = (at + len(text), timestamp, text[-1])
        else:
            super().type_text(timestamp, position, text)


class JumpKeepsTheGroup(Model):
    """Lets typing continue a group across a jump."""

    def jump(self, state: int) -> bool:
        typing = self.typing
        done = super().jump(state)
        self.typing = typing
        return done


class NegativeJumpCountsFromTheEnd(Model):
    """Reads a negative state number as counted from the newest state."""

    def valid_state(self, state: int) -> bool:
        return -len(self.texts) <= state < len(self.texts)

    def jump(self, state: int) -> bool:
        if -len(self.texts) <= state < 0:
            state += len(self.texts)
        return super().jump(state)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2
