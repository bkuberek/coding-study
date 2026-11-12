"""regex-engine promises that its hidden cases catch the classic mistakes of building a regular
expression engine: a parser with the wrong precedence, flattened groups or the wrong error
position, a construction with the wrong shape or numbering, a simulation that counts the wrong
steps or accepts a prefix, and a search that is not leftmost-longest or that misreads a class.
These tests replay every case against a model of the engine written from the statement, which
must give every expected output, and against that model with one mistake planted at a time, which
some hidden case must fail. The model's search tries every start position in turn, unlike the
reference, which makes one pass. A mistake that crashes fails its case, as a thrown exception does
in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0381-regex-engine"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

REPEATERS = {"*": "star", "+": "plus", "?": "opt"}
EMPTY = ("empty",)


class InvalidPatternError(Exception):
    def __init__(self, code: str, at: int) -> None:
        super().__init__(code)
        self.code = code
        self.at = at


class Machine:
    """States numbered from 0, each a printed head (`char 'a'`, `split`) and a list of targets."""

    def __init__(self, heads: list[str], targets: list[list[int]], nodes: list[Any]) -> None:
        self.heads = heads
        self.targets = targets
        self.nodes = nodes
        self.final = heads.index("match")


class Model:
    """The engine as the statement words it, one method per rule; each mistake overrides one."""

    # --- level 1: the parser
    def parse(self, pattern: str) -> str:
        try:
            return self.show(self.tree(pattern))
        except InvalidPatternError as error:
            return f"error: {error.code} at {error.at}"

    def tree(self, pattern: str) -> Any:
        self.src = pattern
        self.i = 0
        self.opens: list[int] = []
        node = self.alternation()
        if self.i < len(self.src):
            raise InvalidPatternError("unmatched-paren", self.i)
        return node

    def ahead(self) -> str:
        return self.src[self.i] if self.i < len(self.src) else ""

    def combine(self, kind: str, parts: list[Any]) -> Any:
        return parts[0] if len(parts) == 1 else (kind, tuple(parts))

    def alternation(self) -> Any:
        sides = [self.sequence()]
        while self.ahead() == "|":
            self.i += 1
            sides.append(self.sequence())
        return self.combine("alt", sides)

    def sequence(self) -> Any:
        items = []
        while self.ahead() not in ("", "|", ")"):
            items.append(self.repetition())
        return self.combine("cat", items) if items else EMPTY

    def repetition(self) -> Any:
        if self.ahead() in REPEATERS:
            raise InvalidPatternError("nothing-to-repeat", self.i)
        node = self.atom()
        while self.ahead() in REPEATERS:
            node = (REPEATERS[self.ahead()], node)
            self.i += 1
        return node

    def atom(self) -> Any:
        at = self.i
        char = self.src[at]
        self.i += 1
        if char == "(":
            return self.group(at)
        if char == ".":
            return ("any",)
        if char == "[":
            return self.char_class(at)
        return self.literal(char)

    def literal(self, char: str) -> Any:
        return ("lit", char)

    def group(self, at: int) -> Any:
        self.opens.append(at)
        inner = self.alternation()
        if self.ahead() != ")":
            raise InvalidPatternError("unclosed-group", self.opens[-1])
        self.opens.pop()
        self.i += 1
        return inner

    def char_class(self, at: int) -> Any:
        negated = self.ahead() == "^"
        if negated:
            self.i += 1
        items: list[tuple[str, str]] = []
        while True:
            if self.i >= len(self.src):
                raise InvalidPatternError("unclosed-class", at)
            if self.ahead() == "]":
                if not items:
                    raise InvalidPatternError("empty-class", at)
                self.i += 1
                return ("class", negated, tuple(items))
            items.append(self.class_item())

    def is_range(self) -> bool:
        return self.ahead() == "-" and self.i + 1 < len(self.src) and self.src[self.i + 1] != "]"

    def class_item(self) -> tuple[str, str]:
        first_at = self.i
        low = self.src[first_at]
        self.i += 1
        if not self.is_range():
            return (low, low)
        high = self.src[self.i + 1]
        if ord(high) < ord(low):
            raise InvalidPatternError("bad-range", first_at)
        self.i += 2
        return (low, high)

    def quote(self, char: str) -> str:
        return "'" + char + "'"

    def show(self, node: Any) -> str:
        kind = node[0]
        if kind == "lit":
            return self.quote(node[1])
        if kind in ("any", "empty"):
            return kind
        if kind == "class":
            words = [
                self.quote(low) if low == high else self.quote(low) + "-" + self.quote(high)
                for low, high in node[2]
            ]
            return ("notclass" if node[1] else "class") + "(" + ",".join(words) + ")"
        if kind in ("cat", "alt"):
            return kind + "(" + ",".join(self.show(part) for part in node[1]) + ")"
        return kind + "(" + self.show(node[1]) + ")"

    # --- level 2: the construction
    def new_state(self, head: str, arrows: int, node: Any = None) -> int:
        self.heads.append(head)
        self.nodes.append(node)
        self.arrows.append([None] * arrows)
        return len(self.heads) - 1

    def point(self, loose: list[tuple[int, int]], target: int) -> None:
        for state, slot in loose:
            self.arrows[state][slot] = target

    def build(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return getattr(self, "build_" + node[0])(node)

    def build_single(self, head: str, node: Any) -> tuple[int, list[tuple[int, int]]]:
        state = self.new_state(head, 1, node)
        return state, [(state, 0)]

    def build_lit(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_single("char " + self.quote(node[1]), node)

    def build_any(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_single("any", node)

    def build_empty(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_single("empty", node)

    def build_class(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_single(self.show(node), node)

    def build_cat(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        start, loose = self.build(node[1][0])
        for part in node[1][1:]:
            part_start, part_loose = self.build(part)
            self.point(loose, part_start)
            loose = part_loose
        return start, loose

    def build_alt(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        split = self.new_state("split", len(node[1]))
        loose: list[tuple[int, int]] = []
        for slot, side in enumerate(node[1]):
            side_start, side_loose = self.build(side)
            self.arrows[split][slot] = side_start
            loose += side_loose
        return split, loose

    def build_star(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        inner, inner_loose = self.build(node[1])
        split = self.new_state("split", 2)
        self.arrows[split][0] = inner
        self.point(inner_loose, split)
        return split, [(split, 1)]

    def build_plus(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        inner, inner_loose = self.build(node[1])
        split = self.new_state("split", 2)
        self.arrows[split][0] = inner
        self.point(inner_loose, split)
        return inner, [(split, 1)]

    def build_opt(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        inner, inner_loose = self.build(node[1])
        split = self.new_state("split", 2)
        self.arrows[split][0] = inner
        return split, [*inner_loose, (split, 1)]

    def order(self, start: int) -> list[int]:
        """Breadth first from the start."""
        found = [start]
        for state in found:
            for target in self.arrows[state]:
                if target not in found:
                    found.append(target)
        return found

    def machine(self, pattern: str) -> Machine:
        self.heads: list[str] = []
        self.nodes: list[Any] = []
        self.arrows: list[list[Any]] = []
        start, loose = self.build(self.tree(pattern))
        self.point(loose, self.new_state("match", 0))
        visit = self.order(start)
        number = {state: index for index, state in enumerate(visit)}
        return Machine(
            [self.heads[state] for state in visit],
            [[number[target] for target in self.arrows[state]] for state in visit],
            [self.nodes[state] for state in visit],
        )

    def nfa(self, pattern: str) -> list[str]:
        machine = self.machine(pattern)
        lines = []
        for state, head in enumerate(machine.heads):
            line = f"{state}: {head}"
            if machine.targets[state]:
                line += " -> " + ", ".join(map(str, machine.targets[state]))
            lines.append(line)
        return lines

    # --- level 3: the simulation
    def silent(self, machine: Machine, state: int) -> bool:
        return machine.heads[state] in ("split", "empty")

    def close(self, machine: Machine, states: list[int]) -> list[int]:
        reached: list[int] = []
        todo = list(states)
        while todo:
            state = todo.pop()
            if state in reached:
                continue
            reached.append(state)
            if self.silent(machine, state):
                todo += machine.targets[state]
        return reached

    def accepts(self, machine: Machine, state: int, char: str) -> bool:
        head = machine.heads[state]
        if head == "any":
            return True
        if head.startswith("char "):
            return head == "char " + self.quote(char)
        if head.startswith(("class(", "notclass(")):
            node = machine.nodes[state]
            return self.in_class(node, char)
        return False

    def in_class(self, node: Any, char: str) -> bool:
        inside = any(ord(low) <= ord(char) <= ord(high) for low, high in node[2])
        return inside != node[1]

    def step(self, machine: Machine, current: list[int], char: str) -> list[int]:
        return [
            machine.targets[state][0] for state in current if self.accepts(machine, state, char)
        ]

    def count(self, machine: Machine, current: list[int]) -> int:
        return len(current)

    def run(self, pattern: str, text: str) -> tuple[bool, int]:
        machine = self.machine(pattern)
        current = self.close(machine, [0])
        steps = self.count(machine, current)
        for char in text:
            current = self.close(machine, self.step(machine, current, char))
            steps += self.count(machine, current)
            if not current:
                return False, steps
        return machine.final in current, steps

    def full_match(self, pattern: str, text: str) -> bool:
        return self.run(pattern, text)[0]

    def count_steps(self, pattern: str, text: str) -> int:
        return self.run(pattern, text)[1]

    # --- level 4: the search, one start position at a time
    def longest_from(self, machine: Machine, text: str, start: int) -> int | None:
        current = self.close(machine, [0])
        last = start if machine.final in current else None
        for position in range(start, len(text)):
            current = self.close(machine, self.step(machine, current, text[position]))
            if not current:
                break
            if machine.final in current:
                last = position + 1
        return last

    def search(self, pattern: str, text: str) -> list[int]:
        machine = self.machine(pattern)
        for start in range(len(text) + 1):
            end = self.longest_from(machine, text, start)
            if end is not None:
                return [start, end]
        return [-1, -1]


# ------------------------------------------------------------------ level 1 mistakes
class AlternationBindsTighter(Model):
    """Splits at `|` inside a sequence, so `ab|cd` is a, then b or c, then d."""

    def sequence(self) -> Any:
        items = []
        while self.ahead() not in ("", ")"):
            if self.ahead() == "|" and items:
                self.i += 1
                items[-1] = ("alt", (items[-1], self.repetition()))
            elif self.ahead() == "|":
                break
            else:
                items.append(self.repetition())
        return self.combine("cat", items) if items else EMPTY


class RepetitionTakesTheWholeSequence(Model):
    """Repeats everything read so far in the sequence, so `ab*` is (ab)*."""

    def sequence(self) -> Any:
        items: list[Any] = []
        while self.ahead() not in ("", "|", ")"):
            if self.ahead() in REPEATERS and items:
                items = [(REPEATERS[self.ahead()], self.combine("cat", items))]
                self.i += 1
            else:
                items.append(self.repetition())
        return self.combine("cat", items) if items else EMPTY

    def repetition(self) -> Any:
        if self.ahead() in REPEATERS:
            raise InvalidPatternError("nothing-to-repeat", self.i)
        return self.atom()


class StackedRepetitionIsAnError(Model):
    """Accepts one repetition operator per piece."""

    def repetition(self) -> Any:
        node = super().repetition()
        if node[0] in ("star", "plus", "opt") and node[1][0] in ("star", "plus", "opt"):
            raise InvalidPatternError("nothing-to-repeat", self.i - 1)
        return node


class GroupsFlattenedIntoTheSequence(Model):
    """Merges a group's sequence into the sequence around it."""

    def combine(self, kind: str, parts: list[Any]) -> Any:
        merged: list[Any] = []
        for part in parts:
            merged += list(part[1]) if part[0] == kind == "cat" else [part]
        return super().combine(kind, merged)


class AlternationsFlattened(Model):
    """Merges a group's alternation into the alternation around it."""

    def combine(self, kind: str, parts: list[Any]) -> Any:
        merged: list[Any] = []
        for part in parts:
            merged += list(part[1]) if part[0] == kind == "alt" else [part]
        return super().combine(kind, merged)


class OnePieceKeepsItsCat(Model):
    """Writes a sequence of one piece as `cat(x)`."""

    def combine(self, kind: str, parts: list[Any]) -> Any:
        return (kind, tuple(parts)) if kind == "cat" else super().combine(kind, parts)


class EmptyWrittenAsCat(Model):
    """Writes an empty sequence as `cat()`."""

    def show(self, node: Any) -> str:
        return "cat()" if node == EMPTY else super().show(node)


class UnclosedGroupReportsTheOutermost(Model):
    """Points at the first `(` still open instead of the last."""

    def group(self, at: int) -> Any:
        self.opens.append(at)
        inner = self.alternation()
        if self.ahead() != ")":
            raise InvalidPatternError("unclosed-group", self.opens[0])
        self.opens.pop()
        self.i += 1
        return inner


class UnclosedGroupAtTheEnd(Model):
    """Reports an open group at the end of the pattern."""

    def group(self, at: int) -> Any:
        inner = self.alternation()
        if self.ahead() != ")":
            raise InvalidPatternError("unclosed-group", len(self.src))
        self.i += 1
        return inner


class RepeatsAnEmptySequence(Model):
    """Lets `*` after `(` or `|` repeat an empty sequence."""

    def repetition(self) -> Any:
        if self.ahead() in REPEATERS:
            node: Any = EMPTY
            while self.ahead() in REPEATERS:
                node = (REPEATERS[self.ahead()], node)
                self.i += 1
            return node
        return super().repetition()


class StrayCloseEndsThePattern(Model):
    """Stops at a stray `)` and parses what came before."""

    def tree(self, pattern: str) -> Any:
        self.src = pattern
        self.i = 0
        self.opens = []
        return self.alternation()


class QuoteEscaped(Model):
    """Writes a quote character as `'\\''`."""

    def quote(self, char: str) -> str:
        return "'\\''" if char == "'" else super().quote(char)


# ------------------------------------------------------------------ level 2 mistakes
class DepthFirstNumbering(Model):
    """Numbers the states depth first."""

    def order(self, start: int) -> list[int]:
        found: list[int] = []
        todo = [start]
        while todo:
            state = todo.pop()
            if state in found:
                continue
            found.append(state)
            todo += reversed(self.arrows[state])
        return found


class NumberedAsCreated(Model):
    """Keeps the order in which the states were created."""

    def order(self, start: int) -> list[int]:
        return [start] + [state for state in range(len(self.heads)) if state != start]


class PlusStartsAtTheSplit(Model):
    """Builds `plus` like `star`, so `X` may be skipped."""

    def build_plus(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_star(node)


class StarStartsInside(Model):
    """Builds `star` like `plus`, so `X` cannot be skipped."""

    def build_star(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        return self.build_plus(node)


class OptionalArrowsSwapped(Model):
    """Gives the `split` of `opt` its way out first."""

    def build_opt(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        inner, inner_loose = self.build(node[1])
        split = self.new_state("split", 2)
        self.arrows[split][1] = inner
        return split, [*inner_loose, (split, 0)]


class AlternationAsBinarySplits(Model):
    """Builds `a|b|c` as a chain of two-way splits."""

    def build_alt(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        sides = node[1]
        if len(sides) <= 2:
            return super().build_alt(node)
        first_start, first_loose = self.build(sides[0])
        rest_start, rest_loose = self.build_alt(("alt", sides[1:]))
        split = self.new_state("split", 2)
        self.arrows[split][0] = first_start
        self.arrows[split][1] = rest_start
        return split, first_loose + rest_loose


class StarLoopsToItsOwnStart(Model):
    """Points the end of `X` back at the start of `X` instead of at the `split`."""

    def build_star(self, node: Any) -> tuple[int, list[tuple[int, int]]]:
        inner, inner_loose = self.build(node[1])
        split = self.new_state("split", 2)
        self.arrows[split][0] = inner
        self.point(inner_loose, inner)
        return split, [(split, 1)]


# ------------------------------------------------------------------ level 3 mistakes
class CountsOnlyCharacterStates(Model):
    """Leaves `split` and `empty` states out of the step count."""

    def count(self, machine: Machine, current: list[int]) -> int:
        return sum(not self.silent(machine, state) for state in current)


class CountsWithoutTheFirstSet(Model):
    """Counts only the sets built after a character."""

    def run(self, pattern: str, text: str) -> tuple[bool, int]:
        matched, steps = super().run(pattern, text)
        return matched, steps - len(self.close(self.machine(pattern), [0]))


class ClosesEachTargetAlone(Model):
    """Adds up the closure of every target on its own, so a state two targets reach counts twice."""

    def run(self, pattern: str, text: str) -> tuple[bool, int]:
        machine = self.machine(pattern)
        current = self.close(machine, [0])
        steps = len(current)
        for char in text:
            targets = self.step(machine, current, char)
            steps += sum(len(self.close(machine, [target])) for target in targets)
            current = self.close(machine, targets)
            if not current:
                return False, steps
        return machine.final in current, steps


class AcceptsAPrefix(Model):
    """Accepts as soon as the match state is reached, without reading the rest."""

    def run(self, pattern: str, text: str) -> tuple[bool, int]:
        machine = self.machine(pattern)
        current = self.close(machine, [0])
        steps = len(current)
        matched = machine.final in current
        for char in text:
            current = self.close(machine, self.step(machine, current, char))
            steps += len(current)
            matched = matched or machine.final in current
            if not current:
                break
        return matched, steps


class ClosureOneArrowDeep(Model):
    """Follows only one silent arrow from each state of the set."""

    def close(self, machine: Machine, states: list[int]) -> list[int]:
        reached = list(dict.fromkeys(states))
        for state in list(reached):
            if self.silent(machine, state):
                for target in machine.targets[state]:
                    if target not in reached:
                        reached.append(target)
        return reached


# ------------------------------------------------------------------ level 4 mistakes
class LeftmostShortest(Model):
    """Stops at the first end found from the leftmost start."""

    def longest_from(self, machine: Machine, text: str, start: int) -> int | None:
        current = self.close(machine, [0])
        if machine.final in current:
            return start
        for position in range(start, len(text)):
            current = self.close(machine, self.step(machine, current, text[position]))
            if machine.final in current:
                return position + 1
            if not current:
                break
        return None


class LongestAnywhere(Model):
    """Takes the longest match in the whole text."""

    def search(self, pattern: str, text: str) -> list[int]:
        machine = self.machine(pattern)
        found = [-1, -1]
        for start in range(len(text) + 1):
            end = self.longest_from(machine, text, start)
            if end is not None and (found[0] == -1 or end - start > found[1] - found[0]):
                found = [start, end]
        return found


class SkipsEmptyMatches(Model):
    """Ignores a match of no characters."""

    def longest_from(self, machine: Machine, text: str, start: int) -> int | None:
        end = super().longest_from(machine, text, start)
        return None if end == start else end


class FirstMatchToFinish(Model):
    """Reports the match that ends first, as a scan that stops at its first match would."""

    def search(self, pattern: str, text: str) -> list[int]:
        machine = self.machine(pattern)
        for end in range(len(text) + 1):
            for start in range(end + 1):
                current = self.close(machine, [0])
                for char in text[start:end]:
                    current = self.close(machine, self.step(machine, current, char))
                if machine.final in current:
                    longest = self.longest_from(machine, text, start)
                    return [start, longest if longest is not None else end]
        return [-1, -1]


class NegationIgnored(Model):
    """Reads `[^...]` as `[...]` when matching."""

    def in_class(self, node: Any, char: str) -> bool:
        return any(ord(low) <= ord(char) <= ord(high) for low, high in node[2])


class RangeEndExcluded(Model):
    """Leaves the last character of a range out."""

    def in_class(self, node: Any, char: str) -> bool:
        inside = any(
            ord(low) <= ord(char) < ord(high) or low == high == char for low, high in node[2]
        )
        return inside != node[1]


class DashBeforeCloseStartsARange(Model):
    """Reads `a-]` as a range from `a` to `]`."""

    def is_range(self) -> bool:
        return self.ahead() == "-" and self.i + 1 < len(self.src)


class CaretAlwaysLiteral(Model):
    """Never negates a class."""

    def char_class(self, at: int) -> Any:
        items: list[tuple[str, str]] = []
        while True:
            if self.i >= len(self.src):
                raise InvalidPatternError("unclosed-class", at)
            if self.ahead() == "]":
                if not items:
                    raise InvalidPatternError("empty-class", at)
                self.i += 1
                return ("class", False, tuple(items))
            items.append(self.class_item())


class CloseBracketOutsideIsAnError(Model):
    """Rejects a `]` outside a class."""

    def literal(self, char: str) -> Any:
        if char == "]":
            raise InvalidPatternError("unmatched-paren", self.i - 1)
        return super().literal(char)


class EmptyClassAllowed(Model):
    """Accepts `[]` as a class with no items."""

    def char_class(self, at: int) -> Any:
        if self.ahead() == "]":
            self.i += 1
            return ("class", False, ())
        return super().char_class(at)


class BadRangeAtTheDash(Model):
    """Points a reversed range at its `-`."""

    def class_item(self) -> tuple[str, str]:
        try:
            return super().class_item()
        except InvalidPatternError as error:
            raise InvalidPatternError(error.code, error.at + 1) from error


class OpenGroupBeforeOpenClass(Model):
    """Reports the open group when the pattern ends inside a class inside it."""

    def group(self, at: int) -> Any:
        try:
            return super().group(at)
        except InvalidPatternError as error:
            if error.code == "unclosed-class":
                raise InvalidPatternError("unclosed-group", at) from error
            raise


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (
        IndexError,
        KeyError,
        ValueError,
        TypeError,
        AttributeError,
        RecursionError,
        InvalidPatternError,
    ):
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


def test_the_backtracking_example_grows_linearly():
    """Level 3 promises that one more letter adds 6 steps, where a backtracker needs about 1.6
    times as many tries."""
    model = Model()
    steps = [model.count_steps("(a|aa)*c", "a" * n) for n in (30, 31, 32)]
    assert steps[1] - steps[0] == steps[2] - steps[1] == 6
    ways = [1, 1]
    while len(ways) <= 60:
        ways.append(ways[-1] + ways[-2])
    assert ways[30] == 1_346_269
    assert 2.4e12 < ways[60] < 2.6e12
