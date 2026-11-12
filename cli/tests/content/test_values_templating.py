"""values-templating promises that its hidden cases catch the classic mistakes of layered values
and templates: lists merged item by item, nulls kept or dropped in the wrong place, keys or list
items in the wrong order, a default that hides false or 0, values escaped or rendered twice,
errors reported where rendering met them instead of where the template breaks, the wrong
truthiness, trimming that eats values, loop variables that leak or fall back to the values, and
schema keywords applied to the wrong kinds or reported in the wrong order. These tests replay
every case against a model written from the statement, which must give every expected output,
and against that model with one mistake planted at a time, which some hidden case must fail.

The model takes another route than the reference: it merges flat maps from JSON Pointer to
value, runs a template as a flat list of instructions with a program counter, and validates
plain Python values."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0343-values-templating"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

SEGMENT = r"(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)"
PATH = rf"{SEGMENT}(?:\.{SEGMENT})*"
NAME = r"[A-Za-z_][A-Za-z0-9_]*"
STRING = r'"(?:[^"\\]|\\["\\])*"'
RESERVED = {"if", "else", "end", "for", "in"}
OUT = re.compile(rf"({PATH})(?: *\| *default *({STRING}))?")
IF = re.compile(rf"if +({PATH})")
FOR = re.compile(rf"for +({NAME})(?: *, *({NAME}))? +in +({PATH})")
TAG = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
MISSING = object()

Flat = dict[str, tuple[str, str, str]]
"""A pointer to (kind, text, layer); containers have the text ''."""


class RenderError(Exception):
    def __init__(self, code: str, at: int, detail: str = "") -> None:
        super().__init__(code)
        self.code, self.at, self.detail = code, at, detail


class Model:
    """The renderer as the statement words it. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.layers: dict[str, list[list[str]]] = {}
        self.schema: list[list[str]] = []

    # --- level 1: layers merged as flat maps from pointer to value
    def set_layer(self, name: str, rows: list[list[str]]) -> bool:
        new = name not in self.layers
        self.place_layer(name, rows)
        return new

    def place_layer(self, name: str, rows: list[list[str]]) -> None:
        self.layers[name] = rows

    def flat(self) -> Flat:
        state: Flat = {}
        for layer, rows in self.layers.items():
            patch = {pointer: (kind, text) for pointer, kind, text in rows}
            for pointer in children("", patch):
                self.apply(state, patch, pointer, layer)
        return state

    def apply(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        kind, _ = patch[pointer]
        if kind == "null":
            self.delete(state, pointer)
        elif kind == "object":
            if state.get(pointer, ("",))[0] != "object":
                self.replace_with_object(state, pointer, layer)
            for child in children(pointer, patch):
                self.apply(state, patch, child, layer)
        else:
            self.copy_value(state, patch, pointer, layer)

    def delete(self, state: Flat, pointer: str) -> None:
        drop(state, pointer)

    def replace_with_object(self, state: Flat, pointer: str, layer: str) -> None:
        drop(state, pointer)
        state[pointer] = ("object", "", layer)

    def copy_value(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        drop(state, pointer)
        for inner, (kind, text) in patch.items():
            if inner == pointer or inner.startswith(pointer + "/"):
                state[inner] = (kind, text, layer)

    def ordered(self, state: Flat) -> list[str]:
        """Pointers compared segment by segment: list items by number, keys as text."""

        def key(pointer: str) -> tuple:
            parts = pointer.split("/")[1:]
            parents = ["/".join(["", *parts[:depth]]) for depth in range(len(parts))]
            return tuple(
                int(part) if state.get(parent, ("object",))[0] == "array" else self.key_order(part)
                for part, parent in zip(parts, parents, strict=True)
            )

        return sorted(state, key=key)

    def key_order(self, key: str) -> Any:
        return key

    def merged(self) -> list[list[str]]:
        state = self.flat()
        return [[p, state[p][0], state[p][1]] for p in self.ordered(state)]

    # --- level 2 and 3: a template compiled to a flat program
    def render(self, template: str) -> list[str]:
        state = self.flat()
        errors = self.validate_state(state)
        if errors:
            return ["error", "invalid_values", "", str(len(errors))]
        try:
            program = self.compile(template)
            return ["ok", self.run(program, nest(state, ""))]
        except RenderError as failure:
            return ["error", failure.code, self.position(template, failure.at), failure.detail]

    def position(self, template: str, at: int) -> str:
        lines = template[:at].split("\n")
        return f"{len(lines)}:{len(lines[-1]) + 1}"

    def compile(self, template: str) -> list[tuple]:
        """One instruction per text run and per tag. Block tags are checked against the stack
        of open blocks as they are met; trimming is applied to the text runs at the end."""
        program: list[tuple] = []
        opened: list[tuple[str, int, bool]] = []
        cursor = 0
        for found in TAG.finditer(template):
            program.append(("text", template[cursor : found.start()]))
            body = found.group(1)
            left = body.startswith("-")
            body = body[1:] if left else body
            right = body.endswith("-")
            body = body[:-1] if right else body
            step = self.instruction(body.strip(" "), found.start(), opened)
            program.append((*step, left, right))
            cursor = found.end()
        rest = template[cursor:]
        if "{{" in rest:
            raise RenderError("unclosed_tag", cursor + rest.index("{{"))
        program.append(("text", rest))
        if opened:
            raise RenderError("unclosed_block", self.unclosed(opened))
        return self.trim(program)

    def unclosed(self, opened: list[tuple[str, int, bool]]) -> int:
        return opened[-1][1]

    def instruction(self, body: str, at: int, opened: list[tuple[str, int, bool]]) -> tuple:
        first = re.split(r"[^A-Za-z0-9_.]", body, maxsplit=1)[0]
        if first in ("if", "else", "end", "for"):
            return self.block(body, at, opened)
        if re.fullmatch(STRING, body):
            return ("lit", at, self.unquote(body))
        match = OUT.fullmatch(body)
        if not match:
            raise RenderError("bad_expression", at)
        default = None if match.group(2) is None else self.unquote(match.group(2))
        return ("out", at, match.group(1), default)

    def block(self, body: str, at: int, opened: list[tuple[str, int, bool]]) -> tuple:
        if body == "end":
            if not opened:
                raise RenderError("unexpected_tag", at)
            opened.pop()
            return ("end", at)
        if body == "else":
            if not self.else_allowed(opened):
                raise RenderError("unexpected_tag", at)
            opened[-1] = (opened[-1][0], opened[-1][1], True)
            return ("else", at)
        if match := IF.fullmatch(body):
            opened.append(("if", at, False))
            return ("if", at, match.group(1))
        if match := FOR.fullmatch(body):
            names = [name for name in match.groups()[:2] if name is not None]
            if len(set(names)) == len(names) and not RESERVED & set(names):
                opened.append(("for", at, False))
                return ("for", at, names, match.group(3))
        raise RenderError("bad_expression", at)

    def else_allowed(self, opened: list[tuple[str, int, bool]]) -> bool:
        return bool(opened) and opened[-1][0] == "if" and not opened[-1][2]

    def unquote(self, literal: str) -> str:
        return re.sub(r"\\([\"\\])", r"\1", literal[1:-1])

    def trim(self, program: list[tuple]) -> list[tuple]:
        steps = list(program)
        for index, step in enumerate(steps):
            if step[0] != "text":
                if step[-2]:
                    steps[index - 1] = ("text", self.strip_end(steps[index - 1][1]))
                if step[-1]:
                    steps[index + 1] = ("text", self.strip_start(steps[index + 1][1]))
        return steps

    def strip_end(self, text: str) -> str:
        return re.sub(r"[ \n]+\Z", "", text)

    def strip_start(self, text: str) -> str:
        return re.sub(r"\A[ \n]+", "", text)

    def jumps(self, program: list[tuple]) -> dict[int, int]:
        """For an if: its else or end; for an else: its end; for a for: its end; for an end:
        the block it closes."""
        target: dict[int, int] = {}
        stack: list[int] = []
        for index, step in enumerate(program):
            if step[0] in ("if", "for"):
                stack.append(index)
            elif step[0] == "else":
                target[stack[-1]] = index
                stack[-1:] = [stack[-1], index]
            elif step[0] == "end":
                start = stack.pop()
                if program[start][0] == "else":
                    target[start] = index
                    start = stack.pop()
                target.setdefault(start, index)
                target[index] = start
        return target

    def run(self, program: list[tuple], values: Any) -> str:
        jumps = self.jumps(program)
        self.values = values
        out: list[str] = []
        frames: list[dict] = []
        pc = 0
        while pc < len(program):
            step = program[pc]
            kind = step[0]
            if kind != "text":
                self.before_tag(step, out)
            if kind == "text":
                self.emit(out, step[1])
            elif kind == "bad":  # never compiled by the model itself, only by a mistake
                raise RenderError("bad_expression", step[1])
            elif kind == "lit":
                self.emit(out, step[2])
            elif kind == "out":
                self.emit(out, self.output(step, values, frames))
            elif kind == "else" or (
                kind == "if" and not self.truthy(self.find(step[2], values, frames))
            ):
                pc = jumps[pc]
            elif kind == "for":
                pairs = self.iterate(step, values, frames)
                if pairs:
                    frames.append({"start": pc, "pairs": pairs, "at": 0, "names": step[2]})
                    self.bind(frames[-1])
                else:
                    pc = jumps[pc]
            elif kind == "end" and program[jumps[pc]][0] == "for":
                frame = frames[-1]
                frame["at"] += 1
                if frame["at"] < len(frame["pairs"]):
                    self.bind(frame)
                    pc = frame["start"]
                else:
                    self.leave(frames)
            pc += 1
        return "".join(out)

    def before_tag(self, step: tuple, out: list[str]) -> None:
        pass

    def emit(self, out: list[str], piece: str) -> None:
        out.append(piece)

    def leave(self, frames: list[dict]) -> None:
        frames.pop()

    def bind(self, frame: dict) -> None:
        key, item = frame["pairs"][frame["at"]]
        names = frame["names"]
        frame["vars"] = (
            dict(zip(names, (key, item), strict=False)) if len(names) == 2 else {names[0]: item}
        )

    def output(self, step: tuple, values: Any, frames: list[dict]) -> str:
        found = self.find(step[2], values, frames)
        if found is MISSING or (step[3] is not None and self.use_default(found)):
            if step[3] is None:
                raise RenderError("missing_value", step[1], self.detail(step[2]))
            return step[3]
        if isinstance(found, (dict, list)):
            raise RenderError("not_scalar", step[1], step[2])
        return self.text_of(found)

    def use_default(self, found: Any) -> bool:
        return False

    def text_of(self, scalar: tuple[str, str]) -> str:
        return scalar[1]

    def detail(self, path: str) -> str:
        return path

    def iterate(self, step: tuple, values: Any, frames: list[dict]) -> list:
        found = self.find(step[3], values, frames)
        if found is MISSING:
            return self.loop_over_missing(step)
        if isinstance(found, list):
            return [(("number", str(self.first_index() + i)), item) for i, item in enumerate(found)]
        if isinstance(found, dict):
            return [(("string", key), found[key]) for key in self.object_keys(found)]
        raise RenderError("not_iterable", step[1], step[3])

    def loop_over_missing(self, step: tuple) -> list:
        raise RenderError("missing_value", step[1], step[3])

    def first_index(self) -> int:
        return 0

    def object_keys(self, members: dict) -> list[str]:
        return sorted(members)

    def find(self, path: str, values: Any, frames: list[dict]) -> Any:
        parts = path.split(".")
        current, rest = values, parts
        for frame in reversed(frames):
            if parts[0] in frame.get("vars", {}):
                current, rest = frame["vars"][parts[0]], parts[1:]
                break
        for part in rest:
            current = self.step_into(current, part)
            if current is MISSING:
                return self.when_lost(path, values)
        return self.null_is_missing(current)

    def null_is_missing(self, value: Any) -> Any:
        return MISSING if value == ("null", "") else value

    def when_lost(self, path: str, values: Any) -> Any:
        return MISSING

    def step_into(self, current: Any, part: str) -> Any:
        if isinstance(current, dict):
            return current.get(part, MISSING)
        if isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", part):
            return current[int(part)] if int(part) < len(current) else MISSING
        return MISSING

    def truthy(self, value: Any) -> bool:
        if value is MISSING:
            return False
        if isinstance(value, (dict, list)):
            return len(value) > 0
        kind, text = value
        return {"boolean": text == "true", "string": text != "", "number": text != "0"}[kind]

    # --- level 4: schema and provenance
    def set_schema(self, rows: list[list[str]]) -> None:
        self.schema = rows

    def validate(self) -> list[list[str]]:
        return self.validate_state(self.flat())

    def validate_state(self, state: Flat) -> list[list[str]]:
        schema = nest({pointer: (kind, text, "") for pointer, kind, text in self.schema}, "")
        errors: list[tuple[str, str, str]] = []
        self.check(nest(state, ""), schema, "", state, errors)
        return [list(error) for error in self.sort_errors(errors)]

    def sort_errors(self, errors: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        return sorted(errors)

    def check(self, value: Any, schema: dict, pointer: str, state: Flat, errors: list) -> None:
        def fail(where: str, keyword: str) -> None:
            errors.append((where, keyword, state[where][2] if where in state else ""))

        if "type" in schema and not self.type_matches(value, schema["type"][1]):
            fail(pointer, "type")
            if self.stop_after_type():
                return
        if "enum" in schema and not self.enum_has(schema["enum"], value):
            fail(pointer, "enum")
        if self.is_number(value):
            if "minimum" in schema and self.below(value, schema["minimum"]):
                fail(pointer, "minimum")
            if "maximum" in schema and self.below(schema["maximum"], value):
                fail(pointer, "maximum")
        if self.is_object(value):
            properties = schema.get("properties", {})
            for name in schema.get("required", []):
                if not isinstance(value, dict) or name[1] not in value:
                    errors.append((self.required_pointer(pointer, name[1]), "required", ""))
            for key, member in value.items() if isinstance(value, dict) else []:
                if key in properties:
                    self.check(member, properties[key], f"{pointer}/{key}", state, errors)
                elif self.closed(schema, properties):
                    fail(f"{pointer}/{key}", "additionalProperties")
            self.check_missing_members(value, schema, pointer, state, errors)
        if isinstance(value, list) and "items" in schema:
            for index, item in enumerate(value):
                self.check(item, schema["items"], f"{pointer}/{index}", state, errors)

    def check_missing_members(self, value, schema, pointer, state, errors) -> None:
        pass

    def is_number(self, value: Any) -> bool:
        return isinstance(value, tuple) and value[0] == "number"

    def is_object(self, value: Any) -> bool:
        return isinstance(value, dict)

    def stop_after_type(self) -> bool:
        return False

    def required_pointer(self, pointer: str, name: str) -> str:
        return f"{pointer}/{name}"

    def closed(self, schema: dict, properties: dict) -> bool:
        return schema.get("additionalProperties") == ("boolean", "false")

    def type_matches(self, value: Any, name: str) -> bool:
        if isinstance(value, dict):
            return name == "object"
        if isinstance(value, list):
            return name == "array"
        return value[0] == name or (value[0] == "number" and name == "integer")

    def enum_has(self, options: list, value: Any) -> bool:
        return isinstance(value, tuple) and value in options

    def below(self, low: tuple[str, str], high: tuple[str, str]) -> bool:
        return int(low[1]) < int(high[1])

    def provenance(self) -> list[list[str]]:
        state = self.flat()
        return [[pointer, state[pointer][2]] for pointer in self.ordered(state)]


def children(pointer: str, rows: Mapping[str, Any]) -> list[str]:
    depth = pointer.count("/") + 1
    return [p for p in rows if p.startswith(pointer + "/") and p.count("/") == depth]


def drop(state: Flat, pointer: str) -> None:
    for inner in [p for p in state if p == pointer or p.startswith(pointer + "/")]:
        del state[inner]


def nest(state: Mapping[str, tuple[str, str, str]], pointer: str) -> Any:
    """Plain values: a dict, a list or a (kind, text) pair."""
    kind = state[pointer][0] if pointer else "object"
    if kind == "object":
        return {p.rsplit("/", 1)[1]: nest(state, p) for p in children(pointer, state)}
    if kind == "array":
        found = children(pointer, state)
        return [nest(state, p) for p in sorted(found, key=lambda p: int(p.rsplit("/", 1)[1]))]
    return (kind, state[pointer][1])


# --- level 1 mistakes
class EmptyObjectKeepsTheOldValue(Model):
    """An empty object in a later layer leaves a scalar where it was."""

    def apply(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        if patch[pointer][0] == "object" and not children(pointer, patch) and pointer in state:
            return
        super().apply(state, patch, pointer, layer)


class ListsMergeItemByItem(Model):
    """A later list overwrites the earlier one item by item and keeps the rest."""

    def copy_value(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        if patch[pointer][0] == "array" and state.get(pointer, ("",))[0] == "array":
            for inner, (kind, text) in patch.items():
                if inner.startswith(pointer + "/"):
                    drop(state, inner)
                    state[inner] = (kind, text, layer)
            return
        super().copy_value(state, patch, pointer, layer)


class NewObjectsCopiedWhole(Model):
    """Copies an object over a non-object as it is, nulls included, instead of merging it into
    an empty object."""

    def apply(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        if patch[pointer][0] == "object" and state.get(pointer, ("",))[0] != "object":
            self.copy_value(state, patch, pointer, layer)
            return
        super().apply(state, patch, pointer, layer)


class NullsDroppedFromLists(Model):
    """A null item inside a copied list is removed."""

    def copy_value(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        super().copy_value(state, patch, pointer, layer)
        for inner in [p for p in state if p.startswith(pointer + "/") and state[p][0] == "null"]:
            del state[inner]


class PointersSortedAsText(Model):
    """Sorts the merged rows by their pointer text, so /arr/10 comes before /arr/2."""

    def ordered(self, state: Flat) -> list[str]:
        return sorted(state)


class KeysSortedIgnoringCase(Model):
    """Sorts keys without regard to case."""

    def key_order(self, key: str) -> Any:
        return key.lower()


class ReplacedLayerMovesToTheEnd(Model):
    """Replacing a layer moves it after every other layer."""

    def place_layer(self, name: str, rows: list[list[str]]) -> None:
        self.layers.pop(name, None)
        self.layers[name] = rows


class NullDeletesOnlyScalars(Model):
    """A null removes a scalar but leaves an object in place."""

    def delete(self, state: Flat, pointer: str) -> None:
        if state.get(pointer, ("",))[0] != "object":
            super().delete(state, pointer)


class SetLayerAlwaysTrue(Model):
    """Reports every set as a new layer."""

    def set_layer(self, name: str, rows: list[list[str]]) -> bool:
        super().set_layer(name, rows)
        return True


class KindsGuessedFromText(Model):
    """Treats the texts true and false as booleans, whatever their kind."""

    def merged(self) -> list[list[str]]:
        rows = super().merged()
        return [
            [pointer, "boolean" if text in ("true", "false") else kind, text]
            for pointer, kind, text in rows
        ]


# --- level 2 mistakes
class DefaultForFalsyValues(Model):
    """Uses the default for false, an empty text and 0 as well as for missing values."""

    def use_default(self, found: Any) -> bool:
        return not self.truthy(found)


class NullPrintsEmpty(Model):
    """Treats a null as a value with an empty text instead of as missing."""

    def null_is_missing(self, value: Any) -> Any:
        return value


class ErrorsWhereRenderingMeetsThem(Model):
    """Reports a malformed tag only when rendering reaches it, so a missing value earlier wins
    and a branch not taken is never checked."""

    def instruction(self, body: str, at: int, opened: list[tuple[str, int, bool]]) -> tuple:
        try:
            return super().instruction(body, at, opened)
        except RenderError as failure:
            if failure.code != "bad_expression":
                raise
            return ("bad", at)


class ColumnsFromZero(Model):
    """Counts columns from 0."""

    def position(self, template: str, at: int) -> str:
        lines = template[:at].split("\n")
        return f"{len(lines)}:{len(lines[-1])}"


class EscapesKept(Model):
    """Leaves the backslashes of a string literal in its text."""

    def unquote(self, literal: str) -> str:
        return literal[1:-1]


class ValuesEscaped(Model):
    """Escapes quotes and backslashes in the values it inserts."""

    def text_of(self, scalar: tuple[str, str]) -> str:
        return scalar[1].replace("\\", "\\\\").replace('"', '\\"')


class ValuesRenderedAgain(Model):
    """Renders the text of a value as a template once more."""

    def text_of(self, scalar: tuple[str, str]) -> str:
        if "{{" not in scalar[1]:
            return scalar[1]
        values = self.values
        text = self.run(self.compile(scalar[1]), values)
        self.values = values
        return text


class UnknownEscapesKept(Model):
    """Accepts any backslash sequence in a string literal and keeps it as text."""

    def instruction(self, body: str, at: int, opened: list[tuple[str, int, bool]]) -> tuple:
        if re.fullmatch(r'"[^"]*"', body):
            return ("lit", at, body[1:-1])
        return super().instruction(body, at, opened)


class ExtraSegmentsIgnored(Model):
    """Stops at a scalar and ignores the rest of the path."""

    def step_into(self, current: Any, part: str) -> Any:
        return current if isinstance(current, tuple) else super().step_into(current, part)


class DetailIsTheLastSegment(Model):
    """Names only the last segment of a missing path."""

    def detail(self, path: str) -> str:
        return path.split(".")[-1]


class ListsPrintAsJson(Model):
    """Prints a list or an object as JSON instead of failing with not_scalar."""

    def output(self, step: tuple, values: Any, frames: list[dict]) -> str:
        found = self.find(step[2], values, frames)
        if isinstance(found, (dict, list)):
            return json.dumps(found)
        return super().output(step, values, frames)


# --- level 3 mistakes
class TextZeroIsFalse(Model):
    """Treats the texts "0" and "false" as false."""

    def truthy(self, value: Any) -> bool:
        if isinstance(value, tuple) and value[1] in ("0", "false"):
            return False
        return super().truthy(value)


class ZeroIsTrue(Model):
    """Treats the number 0 as true."""

    def truthy(self, value: Any) -> bool:
        return value == ("number", "0") or super().truthy(value)


class EmptyListIsTrue(Model):
    """Treats every list and object as true, empty or not."""

    def truthy(self, value: Any) -> bool:
        return isinstance(value, (dict, list)) or super().truthy(value)


class ElseInsideALoop(Model):
    """Accepts an else directly inside a for and ignores it."""

    def block(self, body: str, at: int, opened: list[tuple[str, int, bool]]) -> tuple:
        if body == "else" and opened and opened[-1][0] == "for":
            return ("text", "")
        return super().block(body, at, opened)


class UnclosedReportsTheOutermostBlock(Model):
    """Reports the first open block instead of the innermost one."""

    def unclosed(self, opened: list[tuple[str, int, bool]]) -> int:
        return opened[0][1]


class BranchesLookedUpEagerly(Model):
    """Looks up every value of a template, even in a branch that is not taken."""

    def run(self, program: list[tuple], values: Any) -> str:
        if not any(step[0] == "for" for step in program):
            for step in program:
                if step[0] == "out":
                    self.output(step, values, [])
        return super().run(program, values)


class LoopOverMissingRunsZeroTimes(Model):
    """Loops zero times over a missing value."""

    def loop_over_missing(self, step: tuple) -> list:
        return []


class LoopKeysInInsertionOrder(Model):
    """Walks an object's members in the order the values listed them."""

    def object_keys(self, members: dict) -> list[str]:
        return list(members)


class TrimEatsValues(Model):
    """Trims the output while rendering instead of the template text, so a {{- also eats the
    spaces at the end of a value, and a -}} those at the start of the next one."""

    def trim(self, program: list[tuple]) -> list[tuple]:
        return program

    def before_tag(self, step: tuple, out: list[str]) -> None:
        if step[-2]:
            joined = "".join(out).rstrip(" \n")
            out[:] = [joined]
        self.trim_next = step[-1]

    def emit(self, out: list[str], piece: str) -> None:
        if getattr(self, "trim_next", False):
            piece = piece.lstrip(" \n")
            self.trim_next = piece == ""
        out.append(piece)


class TrimOnlySpaces(Model):
    """Trims spaces but not newlines."""

    def strip_end(self, text: str) -> str:
        return text.rstrip(" ")

    def strip_start(self, text: str) -> str:
        return text.lstrip(" ")


class ShadowFallsBackToTheValues(Model):
    """Looks a path up in the values when the loop variable lacks it."""

    def when_lost(self, path: str, values: Any) -> Any:
        current = values
        for part in path.split("."):
            current = self.step_into(current, part)
            if current is MISSING:
                return MISSING
        return current


class LoopVariablesLeak(Model):
    """Keeps the last binding of a loop after its end."""

    def leave(self, frames: list[dict]) -> None:
        frames[-1]["start"] = -1


class IndexFromOne(Model):
    """Numbers list items from 1 in two-variable loops."""

    def first_index(self) -> int:
        return 1


# --- level 4 mistakes
class ExclusiveBounds(Model):
    """Rejects a value equal to its minimum or maximum."""

    def below(self, low: tuple[str, str], high: tuple[str, str]) -> bool:
        return int(low[1]) <= int(high[1])


class BoundsOnTexts(Model):
    """Applies minimum and maximum to texts that hold a number."""

    def is_number(self, value: Any) -> bool:
        return isinstance(value, tuple) and value[1].lstrip("-").isdigit()


class EnumComparesTextOnly(Model):
    """Compares enum options by text, so 1 equals "1"."""

    def enum_has(self, options: list, value: Any) -> bool:
        return isinstance(value, tuple) and value[1] in {text for _, text in options}


class NumberIsNotInteger(Model):
    """Accepts only the type name integer for a number."""

    def type_matches(self, value: Any, name: str) -> bool:
        if name == "number":
            return False
        return super().type_matches(value, name)


class RequiredOnEveryKind(Model):
    """Applies required to scalars too."""

    def is_object(self, value: Any) -> bool:
        return True


class ClosedOnlyWithProperties(Model):
    """Applies additionalProperties false only when properties is given."""

    def closed(self, schema: dict, properties: dict) -> bool:
        return "properties" in schema and super().closed(schema, properties)


class OpenSchemasAreClosed(Model):
    """Treats any additionalProperties as false."""

    def closed(self, schema: dict, properties: dict) -> bool:
        return "additionalProperties" in schema


class RequiredAtTheObject(Model):
    """Reports a missing member at the object that lacks it."""

    def required_pointer(self, pointer: str, name: str) -> str:
        return pointer


class ChecksInsideMissingObjects(Model):
    """Also reports the required members of a missing object."""

    def check_missing_members(self, value, schema, pointer, state, errors) -> None:
        for key, sub in schema.get("properties", {}).items():
            if key not in value and isinstance(sub, dict):
                for name in sub.get("required", []):
                    errors.append((f"{pointer}/{key}/{name[1]}", "required", ""))


class ErrorsInDocumentOrder(Model):
    """Sorts errors with list indexes compared as numbers."""

    def sort_errors(self, errors: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        def key(error: tuple[str, str, str]) -> tuple:
            parts = [int(p) if p.isdigit() else p for p in error[0].split("/")]
            return ([(isinstance(p, str), p) for p in parts], error[1])

        return sorted(errors, key=key)


class ErrorsByKeywordFirst(Model):
    """Sorts errors by keyword, then pointer."""

    def sort_errors(self, errors: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        return sorted(errors, key=lambda error: (error[1], error[0]))


class TypeErrorStopsTheLocation(Model):
    """Skips the other keywords of a location once its type fails."""

    def stop_after_type(self) -> bool:
        return True


class ObjectBelongsToTheLastLayerTouchingIt(Model):
    """Gives an object to every layer that merges into it."""

    def apply(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        super().apply(state, patch, pointer, layer)
        if patch[pointer][0] == "object" and pointer in state:
            state[pointer] = ("object", "", layer)


class SameValueKeepsTheOlderLayer(Model):
    """Keeps the older layer when a value is written again with the same text."""

    def copy_value(self, state: Flat, patch: dict, pointer: str, layer: str) -> None:
        old = state.get(pointer)
        super().copy_value(state, patch, pointer, layer)
        if old is not None and old[:2] == state[pointer][:2] and patch[pointer][0] != "array":
            state[pointer] = old


class ParsesBeforeValidating(Model):
    """Parses the template before it validates the values."""

    def render(self, template: str) -> list[str]:
        try:
            self.compile(template)
        except RenderError as failure:
            return ["error", failure.code, self.position(template, failure.at), failure.detail]
        return super().render(template)


class SchemasAccumulate(Model):
    """Adds the rows of a new schema to the old one instead of replacing it."""

    def set_schema(self, rows: list[list[str]]) -> None:
        known = {row[0] for row in rows}
        self.schema = [row for row in self.schema if row[0] not in known] + rows


class RootPointerIsASlash(Model):
    """Writes the root's pointer as "/"."""

    def validate_state(self, state: Flat) -> list[list[str]]:
        return [[p or "/", k, layer] for p, k, layer in super().validate_state(state)]


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
    except (IndexError, KeyError, ValueError, TypeError, RenderError):
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


def test_the_hidden_cases_reach_every_error_code():
    codes = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "render" and got[0] == "error":
                codes.add(got[1])
    assert codes == {
        "unclosed_tag",
        "bad_expression",
        "missing_value",
        "not_scalar",
        "unexpected_tag",
        "unclosed_block",
        "not_iterable",
        "invalid_values",
    }
