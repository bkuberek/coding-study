"""`sets.yaml`, the workspace's problem sets
(docs/decisions/0023-problem-sets.md#what-a-write-keeps).

The file is the user's, and PyYAML's dump would lose every comment in it. So a change edits the
text, at the positions PyYAML reports when it composes the file, touching only the lines it must;
then it parses what it would write and compares it with what it meant to write, and refuses, writing
nothing, when they differ.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

import yaml
from yaml.nodes import CollectionNode, MappingNode, Node, ScalarNode, SequenceNode

from coding_study.application.ports import Workspace
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem_sets import (
    DESCRIPTION_KEY,
    PROBLEMS_KEY,
    SETS_FILE,
    SETS_KEY,
    ProblemSet,
    parse_sets,
)

_HEADER = (
    "# Your problem sets: edit by hand, or with cstudy set. The order is the order you study in.\n"
)
_WORKSPACE_ROOT = "."
_STEP = "  "
_NO_WRAP = 1 << 20
_BY_HAND = (
    "cstudy can't make this change and keep the file as you wrote it, so it wrote nothing; "
    "edit the file by hand"
)
_LINK = "it is a symbolic link, so cstudy won't write through it"
_NOT_TEXT = "it is not UTF-8 text"
type _Pair = tuple[Node, Node]


class YamlProblemSets:
    """`ProblemSetStore` on the file in the workspace's root, which may be missing. Every method
    raises ConfigError, leaving the file as it is, for a file that is wrong."""

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    def read(self) -> tuple[ProblemSet, ...]:
        return _parsed(self._text())

    def add(self, problem_set: ProblemSet) -> None:
        text = self._text()
        sets = _parsed(text)
        self._write(_with_new_set(text, problem_set, sets), (*sets, problem_set))

    def set_problems(self, name: str, slugs: tuple[str, ...]) -> None:
        text = self._text()
        sets = _parsed(text)
        changed = next(found for found in sets if found.name == name)
        wanted = replace(changed, slugs=slugs)
        expected = tuple(wanted if found is changed else found for found in sets)
        self._write(_with_problems(text, wanted), expected)

    def rename(self, name: str, new_name: str) -> None:
        text = self._text()
        expected = tuple(
            replace(found, name=new_name) if found.name == name else found
            for found in _parsed(text)
        )
        key = _block_named(text, name).key
        renamed = text[: key.start_mark.index] + _scalar(new_name) + text[key.end_mark.index :]
        self._write(renamed, expected)

    def delete(self, name: str) -> None:
        text = self._text()
        expected = tuple(found for found in _parsed(text) if found.name != name)
        self._write(_without_set(text, name), expected)

    def _text(self) -> str:
        """The file's text, ending in a line break; nothing when there is no file."""
        if not self._workspace.exists(SETS_FILE):
            return ""
        try:
            text = self._workspace.read_text(SETS_FILE)
        except UnicodeDecodeError:
            raise ConfigError(SETS_FILE, [_NOT_TEXT]) from None
        except OSError as error:
            raise ConfigError(SETS_FILE, [f"it can't be read: {error.strerror}"]) from None
        return text if not text or text.endswith("\n") else f"{text}\n"

    def _write(self, text: str, expected: Sequence[ProblemSet]) -> None:
        if not _reads_as(text, expected):
            raise ConfigError(SETS_FILE, [_BY_HAND])
        if self._workspace.absolute(SETS_FILE).is_symlink():
            raise ConfigError(SETS_FILE, [_LINK])
        try:
            self._workspace.write_within(_WORKSPACE_ROOT, SETS_FILE, text)
        except ValueError as error:
            raise ConfigError(SETS_FILE, [str(error)]) from None


def _reads_as(text: str, expected: Sequence[ProblemSet]) -> bool:
    try:
        return _parsed(text) == tuple(expected)
    except ConfigError:
        return False


def _parsed(text: str) -> tuple[ProblemSet, ...]:
    try:
        duplicates = _repeated_names(_sets_node(text))
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigError(SETS_FILE, [_syntax_issue(error)]) from None
    if duplicates:
        raise ConfigError(SETS_FILE, [f"the set {name} is defined twice" for name in duplicates])
    return parse_sets(document)


def _syntax_issue(error: yaml.YAMLError) -> str:
    if isinstance(error, yaml.MarkedYAMLError) and error.problem_mark:
        mark = error.problem_mark
        problem = ", ".join(part for part in (error.context, error.problem) if part)
        return f"line {mark.line + 1}, column {mark.column + 1}: {problem}"
    return str(error)


def _repeated_names(sets: Node | None) -> list[str]:
    """YAML takes the last of a repeated key, so a set would vanish without a word."""
    if not isinstance(sets, MappingNode):
        return []
    names = [_key_text(key) for key, _ in _pairs(sets)]
    return sorted({name for name in names if names.count(name) > 1})


def _pairs(node: MappingNode) -> list[_Pair]:
    return node.value  # type: ignore[no-any-return]


def _key_text(key: Node) -> str:
    return str(key.value) if isinstance(key, ScalarNode) else ""


def _top(text: str) -> MappingNode | None:
    root: Node | None = yaml.compose(text, Loader=yaml.SafeLoader)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    return root if isinstance(root, MappingNode) else None


def _entry(mapping: MappingNode, name: str) -> _Pair | None:
    return next((pair for pair in _pairs(mapping) if _key_text(pair[0]) == name), None)


def _sets_node(text: str) -> Node | None:
    top = _top(text)
    entry = None if top is None else _entry(top, SETS_KEY)
    return None if entry is None else entry[1]


@dataclass(frozen=True, slots=True)
class _Block:
    """A set in the text: its name's node, its value's, and its lines. They start with the comment
    directly above it and end before the next set's, or after the last set's own last line."""

    key: ScalarNode
    value: Node
    first: int
    end: int


def _blocks(text: str, lines: Sequence[str]) -> list[_Block]:
    sets = _sets_node(text)
    if not isinstance(sets, MappingNode) or sets.flow_style:
        return []
    pairs = _pairs(sets)
    if not pairs:
        return []
    firsts = [_above_comments(lines, key.start_mark.line) for key, _ in pairs]
    ends = [*firsts[1:], _last_line(pairs[-1][1]) + 1]
    return [
        _Block(key, value, first, end)  # type: ignore[arg-type]
        for (key, value), first, end in zip(pairs, firsts, ends, strict=True)
    ]


def _block_named(text: str, name: str) -> _Block:
    blocks = _blocks(text, text.splitlines(keepends=True))
    found = next((block for block in blocks if _key_text(block.key) == name), None)
    if found is None:
        raise ConfigError(SETS_FILE, [_BY_HAND])
    return found


def _above_comments(lines: Sequence[str], line: int) -> int:
    while line > 0 and lines[line - 1].lstrip().startswith("#"):
        line -= 1
    return line


def _last_line(node: Node) -> int:
    """The last line that holds `node`: a block collection's end mark is past any comment after
    it, so its last child says instead."""
    if isinstance(node, CollectionNode) and node.value and not node.flow_style:
        last: Node | _Pair = node.value[-1]
        return _last_line(last[1] if isinstance(last, tuple) else last)
    mark = node.end_mark
    return mark.line if mark.column > 0 else mark.line - 1


def _scalar(value: str) -> str:
    """`value` as YAML reads it back: plain when it can be, quoted when a plain `on` would be a
    boolean or a `#` would start a comment."""
    dumped = yaml.safe_dump(value, width=_NO_WRAP, allow_unicode=True)
    return dumped.removesuffix("\n...\n").removesuffix("\n")


def _set_lines(problem_set: ProblemSet, indent: str) -> list[str]:
    inner = indent + _STEP
    lines = [f"{indent}{_scalar(problem_set.name)}:\n"]
    if problem_set.description is not None:
        lines.append(f"{inner}{DESCRIPTION_KEY}: {_scalar(problem_set.description)}\n")
    if not problem_set.slugs:
        return [*lines, f"{inner}{PROBLEMS_KEY}: []\n"]
    return [*lines, f"{inner}{PROBLEMS_KEY}:\n", *_item_lines(problem_set.slugs, inner + _STEP)]


def _item_lines(slugs: Sequence[str], indent: str) -> list[str]:
    return [f"{indent}- {_scalar(slug)}\n" for slug in slugs]


def _with_new_set(text: str, problem_set: ProblemSet, sets: Sequence[ProblemSet]) -> str:
    lines = text.splitlines(keepends=True)
    blocks = _blocks(text, lines)
    if blocks:
        indent = " " * blocks[0].key.start_mark.column
        at = blocks[-1].end
        return "".join([*lines[:at], "\n", *_set_lines(problem_set, indent), *lines[at:]])
    top = _top(text)
    entry = None if top is None else _entry(top, SETS_KEY)
    every_set = [*sets, problem_set]
    new = [line for found in every_set for line in _set_lines(found, _STEP)]
    if entry is None:
        return f"{text or _HEADER}{SETS_KEY}:\n{''.join(new)}"
    key, value = entry
    return _lines_after_key(_without_value(text, key, value), key, new)


def _without_value(text: str, key: Node, value: Node) -> str:
    """`key: value` as `key:`, with whatever follows it on the line."""
    colon = text.index(":", key.end_mark.index)
    return text[: colon + 1] + text[value.end_mark.index :]


def _lines_after_key(text: str, key: Node, new: Sequence[str]) -> str:
    lines = text.splitlines(keepends=True)
    at = key.start_mark.line + 1
    return "".join([*lines[:at], *new, *lines[at:]])


def _with_problems(text: str, wanted: ProblemSet) -> str:
    lines = text.splitlines(keepends=True)
    block = _block_named(text, wanted.name)
    entry = _problems_of(block.value)
    if entry is None:
        return _rewritten_set(lines, block, wanted)
    key, value = entry
    if isinstance(value, SequenceNode) and not value.flow_style and value.value:
        return _with_items(lines, value, wanted.slugs)
    indent = " " * key.start_mark.column + _STEP
    return _lines_after_key(
        _without_value(text, key, value), key, _item_lines(wanted.slugs, indent)
    )


def _problems_of(value: Node) -> _Pair | None:
    """The `problems` entry of a set in block style; None for one to write again."""
    if not isinstance(value, MappingNode) or value.flow_style:
        return None
    return _entry(value, PROBLEMS_KEY)


def _rewritten_set(lines: Sequence[str], block: _Block, wanted: ProblemSet) -> str:
    """A set in flow style, or with no `problems`, in the canonical form; the comment above it and
    what follows it stay."""
    indent = " " * block.key.start_mark.column
    at = block.key.start_mark.line
    end = _last_line(block.value) + 1
    return "".join([*lines[:at], *_set_lines(wanted, indent), *lines[end:]])


def _with_items(lines: Sequence[str], sequence: SequenceNode, slugs: Sequence[str]) -> str:
    """The list's lines in the new order. A slug keeps its own line and the comments above it; a
    comment after the last slug stays where it is."""
    items: list[Node] = sequence.value  # type: ignore[assignment]
    first = _above_comments(lines, items[0].start_mark.line)
    kept: dict[str, Sequence[str]] = {}
    end = first
    for item in items:
        chunk_end = item.end_mark.line + 1
        kept[_key_text(item)] = lines[end:chunk_end]
        end = chunk_end
    item_line = lines[items[0].start_mark.line]
    indent = item_line[: len(item_line) - len(item_line.lstrip())]
    ordered = [
        line
        for slug in slugs
        for line in (kept[slug] if slug in kept else _item_lines((slug,), indent))
    ]
    return "".join([*lines[:first], *ordered, *lines[end:]])


def _without_set(text: str, name: str) -> str:
    """The set's lines gone; after the last set, so are the blank lines that led to it."""
    lines = text.splitlines(keepends=True)
    block = _block_named(text, name)
    first = block.first
    is_last = _key_text(_blocks(text, lines)[-1].key) == name
    while is_last and first > 0 and not lines[first - 1].strip():
        first -= 1
    return "".join([*lines[:first], *lines[block.end :]])
