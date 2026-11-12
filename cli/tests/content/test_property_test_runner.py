"""property-test-runner promises that its hidden cases catch the classic mistakes of a small
property-based testing engine: a random generator that loses or keeps the wrong bits, ranges off
by one, a stream restarted for every run, halving that rounds down, targets outside the range,
list candidates in the wrong order or below the minimum length, a shrinker that takes the wrong
candidate or stops early, composed values shrunk against their generator, discards counted per
run or against the wrong limit, and stateful runs that ignore the precondition or compare too
little. These tests replay every case against a model of the engine written from the statement,
which must give every expected output, and against that model with one mistake planted at a
time, which some hidden case must fail. A mistake that crashes fails its case, as a thrown
exception does in the grader."""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from itertools import pairwise
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0355-property-test-runner"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
WORD = 2**32


class GaveUpError(Exception):
    """The call went above its discard limit."""


class Stream:
    def __init__(self, model: "Model", seed: int) -> None:
        self.model = model
        self.state = seed
        self.discarded = 0

    def draw(self) -> int:
        self.state = self.model.step(self.state)
        return self.state

    def between(self, low: int, high: int) -> int:
        return self.model.pick_between(self.draw(), low, high)

    def discard(self) -> None:
        self.discarded += 1
        if self.model.over_limit(self.discarded):
            raise GaveUpError


# A generator is a dict: its kind, its numbers, its parts.
Gen = dict[str, Any]


class Model:
    """The engine as the statement words it. Generators are dicts read from the words with an
    index that moves along; values are ints, lists and tuples. Each rule is one method, so that
    each mistake below overrides a single one."""

    def __init__(self) -> None:
        self.limit = self.first_limit()

    def first_limit(self) -> int:
        return 100

    # --- random numbers
    def step(self, x: int) -> int:
        x = (x ^ (x << 13)) % WORD
        x = x ^ (x >> 17)
        return (x ^ (x << 5)) % WORD

    def pick_between(self, number: int, low: int, high: int) -> int:
        return low + number % (high - low + 1)

    def over_limit(self, discarded: int) -> bool:
        return discarded > self.limit

    def stream_for_run(self, stream: Stream, seed: int) -> Stream:
        return stream

    # --- generators
    def read(self, words: list[str]) -> Gen:
        head = words.pop(0)
        if head == "int":
            return {"kind": "int", "low": int(words.pop(0)), "high": int(words.pop(0))}
        if head == "list":
            low, high = int(words.pop(0)), int(words.pop(0))
            return {"kind": "list", "min": low, "max": high, "of": self.read(words)}
        if head == "pair":
            first = self.read(words)
            return {"kind": "pair", "parts": [first, self.read(words)]}
        name = words.pop(0)
        return {"kind": "filter", "name": name, "of": self.read(words)}

    def parse(self, text: str) -> Gen:
        return self.read(text.split(" "))

    def make(self, gen: Gen, stream: Stream) -> Any:
        if gen["kind"] == "int":
            return stream.between(gen["low"], gen["high"])
        if gen["kind"] == "list":
            return [
                self.make(gen["of"], stream) for _ in range(stream.between(gen["min"], gen["max"]))
            ]
        if gen["kind"] == "pair":
            first = self.make(gen["parts"][0], stream)
            return (first, self.make(gen["parts"][1], stream))
        value = self.make(gen["of"], stream)
        while not self.lets_through(gen["name"], value):
            stream.discard()
            value = self.make(gen["of"], stream)
        return value

    def show(self, value: Any) -> str:
        if isinstance(value, list):
            return "[" + ",".join(map(self.show, value)) + "]"
        if isinstance(value, tuple):
            return f"({self.show(value[0])},{self.show(value[1])})"
        return str(value)

    def lets_through(self, name: str, value: Any) -> bool:
        tests: dict[str, Callable[[Any], bool]] = {
            "even": lambda v: v % 2 == 0,
            "odd": lambda v: v % 2 == 1,
            "nonzero": lambda v: v != 0,
            "positive": lambda v: v > 0,
            "nonempty": lambda v: v != [],
            "distinct": lambda v: len(set(map(self.show, v))) == len(v),
            "unequal": lambda v: self.show(v[0]) != self.show(v[1]),
        }
        return tests[name](value)

    # --- properties
    def total(self, value: Any) -> int:
        if isinstance(value, int):
            return value
        return sum(self.total(part) for part in value)

    def ordered(self, values: list[int]) -> bool:
        return all(a <= b for a, b in pairwise(values))

    def one_pass(self, values: list[int]) -> list[int]:
        result = list(values)
        for i in range(len(result) - 1):
            if result[i] > result[i + 1]:
                result[i], result[i + 1] = result[i + 1], result[i]
        return result

    def buggy_max(self, values: list[int]) -> int:
        best = 0
        for value in values:
            best = max(best, value)
        return best

    def is_multiple(self, value: int, k: int) -> bool:
        return value % k == 0

    def last_write(self, pairs: list[tuple[Any, Any]]) -> dict[str, str]:
        table = {}
        for key, item in pairs:
            table[self.show(key)] = self.show(item)
        return table

    def first_write(self, pairs: list[tuple[Any, Any]]) -> dict[str, str]:
        table: dict[str, str] = {}
        for key, item in pairs:
            table.setdefault(self.show(key), self.show(item))
        return table

    def satisfies(self, prop: str, value: Any) -> bool:
        name, _, rest = prop.partition(" ")
        k = int(rest) if rest else 0
        rules: dict[str, Callable[[], bool]] = {
            "lt": lambda: value < k,
            "not-multiple": lambda: not self.is_multiple(value, k),
            "sum-lt": lambda: self.total(value) < k,
            "len-lt": lambda: len(value) < k,
            "ordered": lambda: self.ordered(value),
            "sort-ordered": lambda: self.ordered(sorted(value)),
            "one-pass-ordered": lambda: self.ordered(self.one_pass(value)),
            "max-from-zero": lambda: value == [] or self.buggy_max(value) == max(value),
            "keys-distinct": lambda: len({self.show(key) for key, _ in value}) == len(value),
            "map-keeps-last": lambda: self.first_write(value) == self.last_write(value),
        }
        return rules[name]()

    # --- candidates
    def target(self, low: int, high: int) -> int:
        return min(max(0, low), high)

    def half(self, number: int) -> int:
        return int(number / 2)

    def int_options(self, low: int, high: int, value: int) -> list[int]:
        goal = self.target(low, high)
        if value == goal:
            return []
        options = [goal]
        quotient = self.half(value - goal)
        while quotient != 0:
            options.append(value - quotient)
            quotient = self.half(quotient)
        return options

    def chunk_starts(self, n: int, size: int) -> range:
        return range(0, n - size + 1, size)

    def shorter(self, items: list[Any], shortest: int) -> list[list[Any]]:
        n, size, options = len(items), len(items), []
        while size >= 1:
            if n - size >= shortest:
                options += [items[:at] + items[at + size :] for at in self.chunk_starts(n, size)]
            size //= 2
        return options

    def simpler_elements(self, items: list[Any], element: Gen) -> list[list[Any]]:
        return [
            [*items[:at], option, *items[at + 1 :]]
            for at, item in enumerate(items)
            for option in self.options(element, item)
        ]

    def list_options(self, gen: Gen, items: list[Any]) -> list[Any]:
        return self.shorter(items, gen["min"]) + self.simpler_elements(items, gen["of"])

    def pair_options(self, gen: Gen, pair: tuple[Any, Any]) -> list[Any]:
        first, second = pair
        left = [(option, second) for option in self.options(gen["parts"][0], first)]
        right = [(first, option) for option in self.options(gen["parts"][1], second)]
        return left + right

    def filter_options(self, gen: Gen, value: Any) -> list[Any]:
        return [o for o in self.options(gen["of"], value) if self.lets_through(gen["name"], o)]

    def unique(self, value: Any, options: list[Any]) -> list[Any]:
        seen, kept = {self.show(value)}, []
        for option in options:
            if self.show(option) not in seen:
                seen.add(self.show(option))
                kept.append(option)
        return kept

    def options(self, gen: Gen, value: Any) -> list[Any]:
        kind = gen["kind"]
        if kind == "int":
            found = self.int_options(gen["low"], gen["high"], value)
        elif kind == "list":
            found = self.list_options(gen, value)
        elif kind == "pair":
            found = self.pair_options(gen, value)
        else:
            found = self.filter_options(gen, value)
        return self.unique(value, found)

    def next_step(self, options: list[Any], fails: Callable[[Any], bool]) -> Any:
        return next((option for option in options if fails(option)), None)

    def shrink_path(self, gen: Gen, prop: str, value: Any) -> list[Any]:
        path = [value]
        while (
            smaller := self.next_step(self.options(gen, path[-1]), self.breaks(prop))
        ) is not None:
            path.append(smaller)
        return path

    def breaks(self, prop: str) -> Callable[[Any], bool]:
        return lambda value: not self.satisfies(prop, value)

    # --- level 1
    def randoms(self, seed: int, count: int) -> list[int]:
        stream = Stream(self, seed)
        return [stream.draw() for _ in range(count)]

    def generate(self, gen: str, seed: int, count: int) -> list[str]:
        stream, parsed, made = Stream(self, seed), self.parse(gen), []
        try:
            while len(made) < count:
                made.append(self.show(self.make(parsed, stream)))
        except GaveUpError:
            pass
        return made

    def run_all(self, gen: str, prop: str, seed: int, runs: int) -> tuple[str, int, Any]:
        stream, parsed, passed = Stream(self, seed), self.parse(gen), 0
        try:
            for run in range(1, runs + 1):
                value = self.make(parsed, self.stream_for_run(stream, seed))
                if not self.satisfies(prop, value):
                    return "failed", self.run_number(run), value
                passed += 1
        except GaveUpError:
            return "gave up", self.passed_before_giving_up(passed), None
        return "passed", runs, None

    def run_number(self, run: int) -> int:
        return run

    def passed_before_giving_up(self, passed: int) -> int:
        return passed

    def check(self, gen: str, prop: str, seed: int, runs: int) -> str:
        outcome, run, value = self.run_all(gen, prop, seed, runs)
        if outcome == "failed":
            return f"failed {run}: {self.show(value)}"
        if outcome == "gave up":
            return f"gave up after {run}"
        return f"passed {runs}"

    # --- level 2
    def candidates(self, gen: str, seed: int, index: int) -> list[str]:
        stream, parsed = Stream(self, seed), self.parse(gen)
        try:
            values = [self.make(parsed, stream) for _ in range(index)]
        except GaveUpError:
            return []
        return [self.show(option) for option in self.options(parsed, values[-1])]

    def minimize(self, gen: str, prop: str, seed: int, runs: int) -> list[str]:
        outcome, _, value = self.run_all(gen, prop, seed, runs)
        if outcome != "failed":
            return []
        return [self.show(step) for step in self.shrink_path(self.parse(gen), prop, value)]

    # --- level 3
    def set_discard_limit(self, limit: int) -> None:
        self.limit = limit

    # --- level 4
    def queue_answer(self, state: dict[str, Any], bug: str, command: str) -> str:
        items, capacity = state["items"], state["capacity"]
        if command == "size":
            return str(len(items) % capacity if bug == "size-wraps" else len(items))
        if command == "get":
            if not items:
                return "empty"
            if bug == "wrap-lifo" and state["accepted"] > capacity:
                return str(items.pop())
            return str(items.pop(0))
        value = int(command.removeprefix("put "))
        if len(items) == capacity and bug != "full-overwrites":
            return "full"
        if len(items) == capacity:
            items.pop(0)
        elif bug == "repeat-dropped" and self.repeats(items, value):
            state["accepted"] += 1
            return "ok"
        items.append(value)
        state["accepted"] += 1
        return "ok"

    def repeats(self, items: list[int], value: int) -> bool:
        return bool(items) and items[-1] == value

    def fresh(self, capacity: int) -> dict[str, Any]:
        return {"items": [], "capacity": capacity, "accepted": 0}

    def allowed(self, state: dict[str, Any]) -> list[str]:
        return ["put", "get", "size"] if state["items"] else ["put", "size"]

    def draw_sequence(self, capacity: int, stream: Stream, longest: int) -> list[str]:
        model, commands = self.fresh(capacity), []
        for _ in range(stream.between(1, longest)):
            choices = self.allowed(model)
            command = choices[stream.draw() % len(choices)]
            if command == "put":
                command = f"put {stream.between(0, 9)}"
            self.queue_answer(model, "none", command)
            commands.append(command)
        return commands

    def is_valid(self, capacity: int, commands: list[str]) -> bool:
        model = self.fresh(capacity)
        for command in commands:
            if command == "get" and not model["items"]:
                return False
            self.queue_answer(model, "none", command)
        return True

    def disagree(self, capacity: int, bug: str, commands: list[str]) -> bool:
        model, system = self.fresh(capacity), self.fresh(capacity)
        answers = [
            (self.queue_answer(model, "none", c), self.queue_answer(system, bug, c))
            for c in commands
        ]
        return any(expected != got for expected, got in answers)

    def sequence_options(self, capacity: int, commands: list[str]) -> list[list[str]]:
        options = self.shorter(commands, 1)
        for at, command in enumerate(commands):
            if command.startswith("put "):
                options += [
                    [*commands[:at], f"put {smaller}", *commands[at + 1 :]]
                    for smaller in self.int_options(0, 9, int(command[4:]))
                ]
        seen, kept = {", ".join(commands)}, []
        for option in options:
            if ", ".join(option) not in seen:
                seen.add(", ".join(option))
                if self.keep_sequence(capacity, option):
                    kept.append(option)
        return kept

    def keep_sequence(self, capacity: int, commands: list[str]) -> bool:
        return self.is_valid(capacity, commands)

    def replay(self, capacity: int, bug: str, commands: list[str]) -> list[str]:
        model, system, answers = self.fresh(capacity), self.fresh(capacity), []
        for command in commands:
            if command == "get" and not model["items"]:
                answers.append("invalid")
                if self.stop_after_invalid():
                    break
                continue
            self.queue_answer(model, "none", command)
            answers.append(self.queue_answer(system, bug, command))
        return answers

    def stop_after_invalid(self) -> bool:
        return True

    def generate_commands(self, capacity: int, seed: int, count: int, max_length: int) -> list[str]:
        stream = Stream(self, seed)
        return [", ".join(self.draw_sequence(capacity, stream, max_length)) for _ in range(count)]

    def first_failure(
        self, capacity: int, bug: str, seed: int, runs: int, max_length: int
    ) -> list[str]:
        stream = Stream(self, seed)
        for _ in range(runs):
            commands = self.draw_sequence(capacity, stream, max_length)
            if self.disagree(capacity, bug, commands):
                return commands
        return []

    def shrink_failure(
        self, capacity: int, bug: str, seed: int, runs: int, max_length: int
    ) -> list[str]:
        commands = self.first_failure(capacity, bug, seed, runs, max_length)
        while commands:
            options = self.sequence_options(capacity, commands)
            smaller = self.next_step(options, lambda c: self.disagree(capacity, bug, c))
            if smaller is None:
                return commands
            commands = smaller
        return commands


class SignedRightShift(Model):
    """Shifts right with the sign of a signed 32-bit number."""

    def step(self, x: int) -> int:
        x = (x ^ (x << 13)) % WORD
        signed = x - WORD if x >= 2**31 else x
        x = (x ^ (signed >> 17)) % WORD
        return (x ^ (x << 5)) % WORD


class BitsAboveThirtyTwoKept(Model):
    """Keeps the bits above 32 until the end of the step."""

    def step(self, x: int) -> int:
        x ^= x << 13
        x ^= x >> 17
        return (x ^ (x << 5)) % WORD


class RangeOneShort(Model):
    """Takes the remainder by the width of the range, so its high end never comes."""

    def pick_between(self, number: int, low: int, high: int) -> int:
        return low + number % max(high - low, 1)


class StreamRestartsEveryRun(Model):
    """Starts the stream again from the seed for every run."""

    def stream_for_run(self, stream: Stream, seed: int) -> Stream:
        return Stream(self, seed)


class RunsCountedFromZero(Model):
    """Reports the failing run counted from zero."""

    def run_number(self, run: int) -> int:
        return run - 1


class ZeroIsNoMultiple(Model):
    """Treats zero as a number that no K divides."""

    def is_multiple(self, value: int, k: int) -> bool:
        return value != 0 and value % k == 0


class OnePassSortsFully(Model):
    """Sorts the list fully where the buggy sort makes one pass."""

    def one_pass(self, values: list[int]) -> list[int]:
        return sorted(values)


class MaximumStartsAtTheFirstElement(Model):
    """Starts the buggy maximum at the first element, which fixes the bug."""

    def buggy_max(self, values: list[int]) -> int:
        return max(values)


class OrderedMeansIncreasing(Model):
    """Reads ordered as strictly increasing."""

    def ordered(self, values: list[int]) -> bool:
        return all(a < b for a, b in pairwise(values))


class HalvingRoundsDown(Model):
    """Halves with a division that rounds down, and stops when the quotient stops changing."""

    def int_options(self, low: int, high: int, value: int) -> list[int]:
        goal = self.target(low, high)
        if value == goal:
            return []
        options, quotient, previous = [goal], (value - goal) // 2, None
        while quotient not in (0, previous):
            options.append(value - quotient)
            previous, quotient = quotient, quotient // 2
        return options


class TargetIsAlwaysZero(Model):
    """Shrinks toward zero even when the range does not hold it."""

    def target(self, low: int, high: int) -> int:
        return 0


class RemovalsIgnoreTheMinimum(Model):
    """Removes chunks even when the list gets shorter than its minimum."""

    def list_options(self, gen: Gen, items: list[Any]) -> list[Any]:
        return self.shorter(items, 0) + self.simpler_elements(items, gen["of"])


class ChunksStartEverywhere(Model):
    """Removes a chunk at every position, not only at multiples of its size."""

    def chunk_starts(self, n: int, size: int) -> range:
        return range(n - size + 1)


class ElementsBeforeRemovals(Model):
    """Offers simpler elements before shorter lists."""

    def list_options(self, gen: Gen, items: list[Any]) -> list[Any]:
        return self.simpler_elements(items, gen["of"]) + self.shorter(items, gen["min"])


class RepeatsKept(Model):
    """Keeps a candidate that equals an earlier one."""

    def unique(self, value: Any, options: list[Any]) -> list[Any]:
        return [option for option in options if self.show(option) != self.show(value)]


class LastFailingCandidate(Model):
    """Moves to the last candidate that fails instead of the first."""

    def next_step(self, options: list[Any], fails: Callable[[Any], bool]) -> Any:
        failing = [option for option in options if fails(option)]
        return failing[-1] if failing else None


class OneShrinkStep(Model):
    """Stops after the first step."""

    def shrink_path(self, gen: Gen, prop: str, value: Any) -> list[Any]:
        smaller = self.next_step(self.options(gen, value), self.breaks(prop))
        return [value] if smaller is None else [value, smaller]


class PathWithoutTheCounterexample(Model):
    """Leaves the original counterexample out of the path."""

    def shrink_path(self, gen: Gen, prop: str, value: Any) -> list[Any]:
        path = super().shrink_path(gen, prop, value)
        return path[1:] if len(path) > 1 else path


class PairShrinksSecondFirst(Model):
    """Shrinks the second part of a pair first."""

    def pair_options(self, gen: Gen, pair: tuple[Any, Any]) -> list[Any]:
        first, second = pair
        right = [(first, option) for option in self.options(gen["parts"][1], second)]
        left = [(option, second) for option in self.options(gen["parts"][0], first)]
        return right + left


class FilterForgottenWhenShrinking(Model):
    """Offers the inner candidates without the filter."""

    def filter_options(self, gen: Gen, value: Any) -> list[Any]:
        return self.options(gen["of"], value)


class DiscardsCountedPerRun(Model):
    """Starts counting discards again at every run."""

    def stream_for_run(self, stream: Stream, seed: int) -> Stream:
        stream.discarded = 0
        return stream


class LimitReachedIsGivingUp(Model):
    """Gives up when the discards reach the limit instead of going above it."""

    def over_limit(self, discarded: int) -> bool:
        return discarded >= self.limit


class RunInProgressCountsAsPassed(Model):
    """Counts the run that gave up as passed."""

    def passed_before_giving_up(self, passed: int) -> int:
        return passed + 1


class DefaultLimitOfAThousand(Model):
    """Starts with a discard limit of 1000."""

    def first_limit(self) -> int:
        return 1000


class SumOfTheOuterIntegers(Model):
    """Adds only the integers at the top of a value."""

    def total(self, value: Any) -> int:
        if isinstance(value, int):
            return value
        return sum(part for part in value if isinstance(part, int))


class MapCheckedAsDistinctKeys(Model):
    """Fails the map property whenever a key repeats, even with the same value."""

    def first_write(self, pairs: list[tuple[Any, Any]]) -> dict[str, str]:
        if len({self.show(key) for key, _ in pairs}) < len(pairs):
            return {"": "repeat"}
        return super().first_write(pairs)


class GetOfferedOnAnEmptyQueue(Model):
    """Offers get even when the model is empty."""

    def allowed(self, state: dict[str, Any]) -> list[str]:
        return ["put", "get", "size"]


class ValueDrawnBeforeTheCommand(Model):
    """Draws a put's value before choosing the command."""

    def draw_sequence(self, capacity: int, stream: Stream, longest: int) -> list[str]:
        model, commands = self.fresh(capacity), []
        for _ in range(stream.between(1, longest)):
            value = stream.between(0, 9)
            choices = self.allowed(model)
            command = choices[stream.draw() % len(choices)]
            if command == "put":
                command = f"put {value}"
            self.queue_answer(model, "none", command)
            commands.append(command)
        return commands


class ReplayGoesOnAfterInvalid(Model):
    """Keeps sending commands after one that breaks the precondition."""

    def stop_after_invalid(self) -> bool:
        return False


class RepeatComparedWithTheFront(Model):
    """Drops a put that equals the front value instead of the back one."""

    def repeats(self, items: list[int], value: int) -> bool:
        return bool(items) and items[0] == value


class PreconditionIgnoredWhenShrinking(Model):
    """Keeps shrink candidates whose get finds an empty model."""

    def keep_sequence(self, capacity: int, commands: list[str]) -> bool:
        return True


class OnlyTheLastAnswerCompared(Model):
    """Compares only the answers to the last command."""

    def disagree(self, capacity: int, bug: str, commands: list[str]) -> bool:
        model, system = self.fresh(capacity), self.fresh(capacity)
        answers = [
            (self.queue_answer(model, "none", c), self.queue_answer(system, bug, c))
            for c in commands
        ]
        return answers[-1][0] != answers[-1][1]


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
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_cover_every_property_filter_and_bug():
    words = set()
    for case in HIDDEN_CASES:
        for op, arguments in zip(case["ops"], case["args"], strict=True):
            if op in ("generate", "check", "candidates", "minimize"):
                words.update(arguments[0].split(" "))
            if op in ("check", "minimize"):
                words.add(arguments[1].split(" ")[0])
            if op in ("replay", "firstFailure", "shrinkFailure"):
                words.add(arguments[1])
    assert {
        "lt",
        "not-multiple",
        "sum-lt",
        "len-lt",
        "ordered",
        "sort-ordered",
        "one-pass-ordered",
        "max-from-zero",
        "keys-distinct",
        "map-keeps-last",
        "even",
        "odd",
        "nonzero",
        "positive",
        "nonempty",
        "distinct",
        "unequal",
        "pair",
        "none",
        "size-wraps",
        "full-overwrites",
        "repeat-dropped",
        "wrap-lifo",
    } <= words
