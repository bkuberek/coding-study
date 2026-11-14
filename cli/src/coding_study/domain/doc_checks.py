"""The static checks of the user docs, D2 to D6, as docs/specs/user-docs.md#static-checks lists
them. D1, the front matter and its schema, is the adapter's.

D6 reads every `cstudy` command a page names in a shell block or in inline code and checks it
against `cstudy`'s command line (docs/specs/user-docs.md#accuracy), which the caller describes as a
`CommandSpec`, so the domain knows no command-line library.
"""

import re
import shlex
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from coding_study.domain.concept_guides import is_slug
from coding_study.domain.errors import ContentIssue
from coding_study.domain.user_docs import DOCS_DIRECTORY, PAGE_SUFFIX, DocPage, heading_ids

PLACEHOLDER = "TODO"
WEB_LINK = "https://"
PROGRAM = "cstudy"
END_OF_OPTIONS = "--"
SHELL_FENCES = frozenset({"", "bash", "sh", "shell", "console", "zsh", "text"})
"""The fences whose lines are read for commands: a shell's, a terminal's text, or no language."""
SEPARATORS = "|&;"
"""The characters a shell ends a command at: `|`, `||`, `&&`, `;`."""
LINK_RULE = "link to a page (<slug>.md), a heading (#<id>) or an https:// address"
_FENCE = re.compile(r"\s*(?P<marker>`{3,}|~{3,})(?P<info>.*)")
_INLINE_CODE = re.compile(r"(?P<ticks>`+)(?P<code>.+?)(?P=ticks)")
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?P<target>[^)\s]*)[^)]*\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HTML_TAG = re.compile(r"</?(?P<name>[A-Za-z][A-Za-z0-9-]*)(?:\s[^<>]*)?/?>")
_PAGE_LINK = re.compile(r"(?P<slug>[^/#]+)\.md(?:#(?P<id>.+))?")
_PLACEHOLDER = re.compile(r"<[^>]*>|\.\.\.|…")
_TABLE_PIPE = "\\|"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """A command of `cstudy`, or `cstudy` itself, as D6 checks a page against it."""

    options: Mapping[str, bool] = field(default_factory=dict[str, bool])
    """Each flag it takes, such as `--lang`, and whether the flag takes a value."""
    subcommands: Mapping[str, "CommandSpec"] = field(default_factory=dict[str, "CommandSpec"])
    """For a group, such as `cstudy set`, its commands by name."""


@dataclass(frozen=True, slots=True)
class CommandMention:
    line: int
    """The index of its line in the page."""
    text: str
    """The line of a shell block, or the inline code span, that holds it."""


def page_file(slug: str) -> str:
    return f"{DOCS_DIRECTORY}/{slug}{PAGE_SUFFIX}"


def page_static_checks(
    file: str, page: DocPage, pages: Mapping[str, DocPage]
) -> list[ContentIssue]:
    """D3 and D5 of one page; `pages` is every page, by slug, for the links."""
    return [*_body_issues(file, page), *_link_issues(file, page, pages)]


def folder_issues(names: Iterable[str]) -> list[ContentIssue]:
    """D2: each entry of `user-docs/`, a folder's name ending in `/`, is a `<slug>.md` file."""
    return [
        ContentIssue(f"{DOCS_DIRECTORY}/{name}", "", "not a page: a file named <slug>.md")
        for name in names
        if not (name.endswith(PAGE_SUFFIX) and is_slug(name.removesuffix(PAGE_SUFFIX)))
    ]


def order_issues(pages: Sequence[DocPage]) -> dict[str, list[ContentIssue]]:
    """D4: no two pages share an order, and a section's pages follow one another. Each issue is
    the later page's, by its slug."""
    found: dict[str, list[ContentIssue]] = {}
    orders: dict[int, str] = {}
    closed: set[str] = set()
    previous: str | None = None
    for page in sorted(pages, key=lambda page: (page.order, page.slug)):
        file = page_file(page.slug)
        if page.order in orders:
            message = f"{page.order} is also the order of {orders[page.order]}"
            found.setdefault(page.slug, []).append(ContentIssue(file, "order", message))
        orders.setdefault(page.order, page.slug)
        if page.section != previous and page.section in closed and previous is not None:
            message = (
                f'comes after a page of "{previous}", apart from the other pages of '
                f'"{page.section}"'
            )
            found.setdefault(page.slug, []).append(ContentIssue(file, "section", message))
        if previous is not None and page.section != previous:
            closed.add(previous)
        previous = page.section
    return found


def command_mentions(markdown: str) -> Iterator[CommandMention]:
    """The lines of shell blocks and the inline code spans that hold the word `cstudy`. In a
    table, `\\|` in a span is `|`."""
    fence: tuple[str, str] | None = None
    for index, line in enumerate(markdown.splitlines()):
        opening = _FENCE.fullmatch(line)
        if fence is None and opening is not None:
            info = opening["info"].strip().split(maxsplit=1)
            fence = (opening["marker"], info[0].lower() if info else "")
            continue
        if fence is not None:
            marker, language = fence
            if opening is not None and _closes(opening, marker):
                fence = None
            elif language in SHELL_FENCES and _names_program(line):
                yield CommandMention(index, line)
            continue
        for span in _INLINE_CODE.finditer(line):
            code = span["code"].replace(_TABLE_PIPE, "|")
            if _names_program(code):
                yield CommandMention(index, code)


def command_issues(file: str, page: DocPage, program: CommandSpec) -> list[ContentIssue]:
    """D6: every command the page names is one `program` has, with flags it takes."""
    return [
        ContentIssue(file, f"line {page.first_line + mention.line + 1}", message)
        for mention in command_mentions(page.markdown)
        for words in _commands(mention.text)
        for message in _command_problems(words, program)
    ]


def _body_issues(file: str, page: DocPage) -> list[ContentIssue]:
    """D3: `# <title>` first, then no TODO, and no HTML tag or image outside code."""
    issues: list[ContentIssue] = []
    lines = page.markdown.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), 0)
    if first >= len(lines) or lines[first] != f"# {page.title}":
        issues.append(ContentIssue(file, _line(page, first), f"starts with # {page.title}"))
    for index, line in enumerate(lines):
        if PLACEHOLDER in line:
            issues.append(ContentIssue(file, _line(page, index), f"holds {PLACEHOLDER}"))
    for index, prose in _prose_lines(lines):
        tag = _HTML_TAG.search(prose)
        if tag is not None:
            issues.append(ContentIssue(file, _line(page, index), f"holds HTML: <{tag['name']}>"))
        if _IMAGE.search(prose):
            message = "holds an image, which does not ship"
            issues.append(ContentIssue(file, _line(page, index), message))
    return issues


def _link_issues(file: str, page: DocPage, pages: Mapping[str, DocPage]) -> list[ContentIssue]:
    """D5: links name a page and one of its headings, a heading of this page, or the web."""
    issues: list[ContentIssue] = []
    for index, prose in _prose_lines(page.markdown.splitlines()):
        for link in _LINK.finditer(prose):
            problem = _link_problem(link["target"], page, pages)
            if problem is not None:
                message = f"links to {link['target']}: {problem}"
                issues.append(ContentIssue(file, _line(page, index), message))
    return issues


def _link_problem(target: str, page: DocPage, pages: Mapping[str, DocPage]) -> str | None:
    if target.startswith(WEB_LINK):
        return None
    if target.startswith("#"):
        return _heading_problem(page, target[1:])
    named = _PAGE_LINK.fullmatch(target)
    if named is None:
        return LINK_RULE
    other = pages.get(named["slug"])
    if other is None:
        return f'there is no page "{named["slug"]}"'
    return None if named["id"] is None else _heading_problem(other, named["id"])


def _heading_problem(page: DocPage, heading: str) -> str | None:
    ids = {found.id for found in heading_ids(page.markdown)}
    return None if heading in ids else f'{page.slug}{PAGE_SUFFIX} has no heading "{heading}"'


def _prose_lines(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    """Each line outside fenced blocks, without its inline code."""
    marker: str | None = None
    for index, line in enumerate(lines):
        opening = _FENCE.fullmatch(line)
        if marker is None and opening is not None:
            marker = opening["marker"]
        elif marker is not None:
            if opening is not None and _closes(opening, marker):
                marker = None
        else:
            yield index, _INLINE_CODE.sub("", line)


def _closes(fence: re.Match[str], marker: str) -> bool:
    found = fence["marker"]
    return found[0] == marker[0] and len(found) >= len(marker) and not fence["info"].strip()


def _line(page: DocPage, index: int) -> str:
    return f"line {page.first_line + index + 1}"


def _names_program(text: str) -> bool:
    return PROGRAM in text.split()


def _commands(text: str) -> Iterator[list[str]]:
    """Each command of `text` that runs `cstudy`: the words after it, up to the end of the
    command. Text a shell cannot split, such as output with a lone quote, splits at spaces."""
    words = _words(text)
    command: list[str] = []
    for word in [*words, ";"]:
        if word and all(character in SEPARATORS for character in word):
            if PROGRAM in command:
                yield command[command.index(PROGRAM) + 1 :]
            command = []
        else:
            command.append(word)


def _words(text: str) -> list[str]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars=SEPARATORS)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return text.split()


def _command_problems(words: list[str], program: CommandSpec) -> Iterator[str]:
    """What is wrong with `cstudy <words>`: a command it does not have, or a flag the command
    does not take. Global flags may come before the command."""
    spec = program
    path = [PROGRAM]
    position = 0
    while position < len(words):
        word = words[position].strip("[]")
        position += 1
        if word == END_OF_OPTIONS:
            return
        if word.startswith("-") and len(word) > 1:
            name, has_value, _value = word.partition("=")
            takes_value = spec.options.get(name)
            if takes_value is None:
                yield f"{' '.join(path)} has no flag {name}"
            elif takes_value and not has_value:
                position += 1
        elif spec.subcommands:
            if _PLACEHOLDER.search(word):
                return
            if word not in spec.subcommands:
                yield f"{' '.join(path)} has no command {word}"
                return
            spec = spec.subcommands[word]
            path.append(word)
