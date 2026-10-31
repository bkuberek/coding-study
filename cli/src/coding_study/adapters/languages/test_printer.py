"""Documents, and the printer that lays them out, for generated test files
(docs/specs/problem-format.md#generated-test-files).

A document is text with the places it may break. The printer is Prettier's (`printDocToString` in
Prettier 3), which ruff's formatter shares: a group keeps its content on one line when that fits
the line length, and otherwise breaks every `Line` directly in it, deciding groups from left to
right. A group is measured up to the next place a later group could break, as if that group were
broken. A group with alternatives tries them in turn, each laid out flat up to its first forced
break, and takes the last one when none fits. A fill packs its items onto each line, as many as
fit. A group that must break, or holds a `BreakParent`, breaks every group around it up to the
nearest group with alternatives.

Each generator builds documents the way its formatter would, so the text needs no formatter.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum, auto


@dataclass(frozen=True, slots=True)
class Text:
    text: str


@dataclass(frozen=True, slots=True)
class Line:
    """A line break when its group breaks, else `flat`: nothing, or a space."""

    flat: str


@dataclass(frozen=True, slots=True)
class Indent:
    content: "Doc"


@dataclass(frozen=True, slots=True, eq=False)
class GroupId:
    """Names a group, so that an `IfBreak` elsewhere can follow how it was laid out."""


@dataclass(frozen=True, slots=True)
class Group:
    """Laid out on one line when it fits, else with every `Line` directly in it broken."""

    content: "Doc"
    breaks: bool = False
    """Always broken, whether or not it fits."""
    alternatives: tuple["Doc", ...] = ()
    """When the content does not fit: the layouts to try in turn, the last one broken."""
    id: GroupId | None = None


@dataclass(frozen=True, slots=True)
class IfBreak:
    """`broken` where its group breaks, else `flat`; its group is the enclosing one, or the
    group named `group`."""

    broken: "Doc"
    flat: "Doc" = ()
    group: GroupId | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    """Items and the separators between them, `(item, separator, item, ...)`: each separator
    breaks only when the item after it does not fit on the line."""

    parts: tuple["Doc", ...]


@dataclass(frozen=True, slots=True)
class BreakParent:
    """Breaks the enclosing group."""


type Doc = Text | Line | Indent | Group | IfBreak | Fill | BreakParent | tuple[Doc, ...]

SOFT_LINE = Line("")
SPACE_OR_LINE = Line(" ")
_TRAILING_WHITESPACE = " \t"


@dataclass(frozen=True, slots=True)
class Style:
    line_length: int
    indent: str
    """One level of indentation."""
    width: Callable[[str], int]
    """The columns the formatter counts for a text."""


def will_break(doc: Doc) -> bool:
    """Whether `doc` holds a group that must break, or a `BreakParent`, outside alternatives."""
    match doc:
        case Group(content, breaks):
            return breaks or will_break(content)
        case BreakParent():
            return True
        case tuple():
            return any(will_break(part) for part in doc)
        case Indent(content):
            return will_break(content)
        case Fill(parts):
            return any(will_break(part) for part in parts)
        case IfBreak(broken, flat):
            return will_break(broken) or will_break(flat)
        case _:
            return False


def layout(doc: Doc, style: Style, indent: str) -> str:
    """`doc` laid out from the start of a line at `indent`, which the text starts with."""
    return _Printer(doc, style).print(indent)


class _Mode(Enum):
    BREAK = auto()
    FLAT = auto()


@dataclass(frozen=True, slots=True)
class _Command:
    indent: str
    mode: _Mode
    doc: Doc


@dataclass(slots=True)
class _Printer:
    doc: Doc
    style: Style
    _broken: set[int] = field(default_factory=set[int])
    """The ids of the groups that break, given or propagated."""
    _modes: dict[GroupId, _Mode] = field(default_factory=dict[GroupId, _Mode])

    def print(self, indent: str) -> str:
        self._propagate_breaks(self.doc)
        output, column = [indent], self.style.width(indent)
        commands = [_Command(indent, _Mode.BREAK, self.doc)]
        while commands:
            command = commands.pop()
            match command.doc:
                case tuple():
                    commands += [
                        _Command(command.indent, command.mode, part)
                        for part in reversed(command.doc)
                    ]
                case Indent(content):
                    commands.append(
                        _Command(command.indent + self.style.indent, command.mode, content)
                    )
                case Group() as group:
                    commands.append(self._group(group, command, commands, column))
                    if group.id is not None:
                        self._modes[group.id] = commands[-1].mode
                case Fill(parts) if parts:
                    commands += self._fill(parts, command, column)
                case IfBreak(broken, flat, group_id):
                    mode = self._modes.get(group_id) if group_id else command.mode
                    if mode is not None:
                        chosen = broken if mode is _Mode.BREAK else flat
                        commands.append(_Command(command.indent, command.mode, chosen))
                case Line() if command.mode is _Mode.BREAK:
                    _trim(output)
                    output.append(f"\n{command.indent}")
                    column = self.style.width(command.indent)
                case Line(text) | Text(text):
                    output.append(text)
                    column += self.style.width(text)
                case _:
                    pass
        return "".join(output)

    def _group(
        self, group: Group, command: _Command, rest: list[_Command], column: int
    ) -> _Command:
        broken = id(group) in self._broken
        if command.mode is _Mode.FLAT:
            return _Command(command.indent, _Mode.BREAK if broken else _Mode.FLAT, group.content)
        flat = _Command(command.indent, _Mode.FLAT, group.content)
        remaining = self.style.line_length - column
        if not broken and self._fits(flat, rest, remaining):
            return flat
        if not group.alternatives:
            return _Command(command.indent, _Mode.BREAK, group.content)
        most_expanded = _Command(command.indent, _Mode.BREAK, group.alternatives[-1])
        if broken:
            return most_expanded
        for alternative in group.alternatives:
            candidate = _Command(command.indent, _Mode.FLAT, alternative)
            if self._fits(candidate, rest, remaining):
                return candidate
        return most_expanded

    def _fill(self, parts: tuple[Doc, ...], command: _Command, column: int) -> list[_Command]:
        """The commands for the first item and separator, then for the rest of the fill."""
        remaining = self.style.line_length - column
        item, *others = parts
        flat_item = _Command(command.indent, _Mode.FLAT, item)
        broken_item = _Command(command.indent, _Mode.BREAK, item)
        item_fits = self._fits(flat_item, [], remaining, must_be_flat=True)
        if not others:
            return [flat_item if item_fits else broken_item]
        separator, *after = others
        flat_separator = _Command(command.indent, _Mode.FLAT, separator)
        broken_separator = _Command(command.indent, _Mode.BREAK, separator)
        if not after:
            return [flat_separator, flat_item] if item_fits else [broken_separator, broken_item]
        rest = _Command(command.indent, command.mode, Fill(tuple(after)))
        pair = _Command(command.indent, _Mode.FLAT, (item, separator, after[0]))
        if self._fits(pair, [], remaining, must_be_flat=True):
            return [rest, flat_separator, flat_item]
        if item_fits:
            return [rest, broken_separator, flat_item]
        return [rest, broken_separator, broken_item]

    def _fits(
        self, first: _Command, rest: list[_Command], width: int, *, must_be_flat: bool = False
    ) -> bool:
        """Whether `first` fits in `width` columns on one line, together with what follows it up
        to the next line break; a group that follows is measured in its mode, so up to its first
        line when it breaks. A space counts only once text follows it."""
        pending, remaining, space_pending = [first], len(rest), False
        while width >= 0:
            if not pending:
                if not remaining:
                    return True
                remaining -= 1
                pending.append(rest[remaining])
                continue
            command = pending.pop()
            match command.doc:
                case Text(text) if text:
                    width -= self.style.width(text) + (1 if space_pending else 0)
                    space_pending = False
                case tuple() | Fill():
                    parts = command.doc if isinstance(command.doc, tuple) else command.doc.parts
                    pending += [_Command("", command.mode, part) for part in reversed(parts)]
                case Indent(content):
                    pending.append(_Command("", command.mode, content))
                case Group() as group:
                    broken = id(group) in self._broken
                    if must_be_flat and broken:
                        return False
                    mode = _Mode.BREAK if broken else command.mode
                    alternatives = group.alternatives
                    most_expanded = alternatives and mode is _Mode.BREAK
                    content = alternatives[-1] if most_expanded else group.content
                    pending.append(_Command("", mode, content))
                case IfBreak(broken, flat, group_id):
                    mode = self._modes.get(group_id, _Mode.FLAT) if group_id else command.mode
                    pending.append(
                        _Command("", command.mode, broken if mode is _Mode.BREAK else flat)
                    )
                case Line() if command.mode is _Mode.BREAK:
                    return True
                case Line(flat):
                    space_pending = space_pending or bool(flat)
                case _:
                    pass
        return False

    def _propagate_breaks(self, doc: Doc) -> bool:
        """Records every group that breaks; whether `doc` breaks the group around it. A break
        inside a group with alternatives stays there: each alternative breaks on its own."""
        match doc:
            case Group(content, breaks, alternatives):
                if id(doc) in self._broken:
                    return True
                inside_breaks = self._propagate_through((content, *alternatives))
                broken = breaks or (inside_breaks and not alternatives)
                if broken:
                    self._broken.add(id(doc))
                return broken
            case BreakParent():
                return True
            case tuple() | Fill():
                return self._propagate_through(doc if isinstance(doc, tuple) else doc.parts)
            case Indent(content):
                return self._propagate_breaks(content)
            case IfBreak(broken, flat):
                return self._propagate_through((broken, flat))
            case _:
                return False

    def _propagate_through(self, parts: tuple[Doc, ...]) -> bool:
        """Visits every part, so that each group in them is recorded; whether one breaks the
        group around them."""
        breaks = [self._propagate_breaks(part) for part in parts]
        return any(breaks)


def _trim(output: list[str]) -> None:
    """Drops the spaces and tabs that end the line, before it breaks."""
    while output and not output[-1].strip(_TRAILING_WHITESPACE):
        output.pop()
    if output:
        output[-1] = output[-1].rstrip(_TRAILING_WHITESPACE)


def flattened(doc: Doc) -> Iterator[Doc]:
    """The parts of `doc` in order, through sequences and indentation."""
    match doc:
        case tuple():
            for part in doc:
                yield from flattened(part)
        case Indent(content):
            yield from flattened(content)
        case _:
            yield doc
