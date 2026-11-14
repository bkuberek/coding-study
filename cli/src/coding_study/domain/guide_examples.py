"""A guide's examples in several languages (docs/specs/guides.md#variants): the language of a file
of `examples/`, the runs of `guide.md` that make one example with variants, the variant shown
(docs/specs/guides.md#the-language-shown), and the guide as `cstudy learn` prints it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_study.domain.guide_markdown import EXAMPLES_PREFIX, OUTPUT, Fence, GuideMarkdown
from coding_study.domain.problem import ALL_LANGUAGES

BASH = "bash"
PYTHON = "python"
JAVASCRIPT = "javascript"
PSEUDOCODE = "pseudocode"
"""The fence of language-neutral pseudocode, which names no file
(docs/specs/guides.md#pseudocode)."""
TARGET_LANGUAGES = tuple(language.value for language in ALL_LANGUAGES)
"""The six languages of cstudy, which every example with variants aims for."""
SHELL_TARGET = (BASH, *TARGET_LANGUAGES)
"""What an example of a shell guide aims for."""
TAB_ORDER = (BASH, *TARGET_LANGUAGES, JAVASCRIPT)
"""The fixed order of the variants, in guide.md and as tabs."""
EXAMPLE_LANGUAGES: Mapping[str, str] = {
    ".sh": BASH,
    ".py": PYTHON,
    ".ts": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".js": JAVASCRIPT,
    ".mjs": JAVASCRIPT,
}
"""What an example may be written in, by extension, and the language its fence names."""
_MINIMUM_VARIANTS = 2


def suffix(name: str) -> str:
    """`.py` for `examples/count.py`; "" for a name without one."""
    base = name.rsplit("/", 1)[-1]
    return f".{base.rsplit('.', 1)[1]}" if "." in base else ""


def stem(name: str) -> str:
    """`examples/count` for `examples/count.py`: what the variants of one example share."""
    return name.removesuffix(suffix(name))


def example_language(name: str) -> str | None:
    return EXAMPLE_LANGUAGES.get(suffix(name))


def tab_rank(language: str) -> int:
    return TAB_ORDER.index(language) if language in TAB_ORDER else len(TAB_ORDER)


@dataclass(frozen=True, slots=True)
class ExampleVariant:
    fence: Fence
    output: Fence

    @property
    def name(self) -> str:
        """The file's path relative to the guide: `examples/count.py`."""
        return self.fence.argument or ""

    @property
    def language(self) -> str:
        return example_language(self.name) or self.fence.language


@dataclass(frozen=True, slots=True)
class ExampleGroup:
    """One example with variants: two or more blocks of one base name, each followed by its own
    output block, with nothing but blank lines between the blocks."""

    variants: tuple[ExampleVariant, ...]

    @property
    def stem(self) -> str:
        return stem(self.variants[0].name)

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(variant.language for variant in self.variants)

    @property
    def start(self) -> int:
        """The line index of the first variant's opening fence."""
        return self.variants[0].fence.start

    @property
    def end(self) -> int:
        """The line index of the last output block's closing fence."""
        return self.variants[-1].output.end


@dataclass(frozen=True, slots=True)
class LanguageChoice:
    """What picks the variant shown: the reader's choice, `default_lang`, and the command that
    picks another, which `cstudy learn` names after each example with variants."""

    chosen: str | None = None
    default_language: str = PYTHON
    others_hint: str = ""


def example_groups(markdown: GuideMarkdown) -> tuple[ExampleGroup, ...]:
    """Every example with variants, in the order of the guide."""
    groups: list[ExampleGroup] = []
    run: list[ExampleVariant] = []
    fences = markdown.fences
    index = 0
    while index < len(fences):
        variant = _variant_at(markdown, index)
        if variant is None:
            _close(run, groups)
            index += 1
            continue
        if run and not _continues(markdown, run[-1], variant):
            _close(run, groups)
        run.append(variant)
        index += 2
    _close(run, groups)
    return tuple(groups)


def shown_language(languages: Sequence[str], chosen: str | None, default_language: str) -> str:
    """The first of the reader's choice, bash, `default_lang` and Python that the example has,
    else its first language in the tab order."""
    for wanted in (chosen, BASH, default_language, PYTHON):
        if wanted is not None and wanted in languages:
            return wanted
    return min(languages, key=tab_rank)


def missing_languages(group: ExampleGroup, *, shell: bool) -> tuple[str, ...]:
    """The languages of its target that the example has no variant in yet."""
    target = SHELL_TARGET if shell else TARGET_LANGUAGES
    return tuple(language for language in target if language not in group.languages)


def terminal_text(markdown: GuideMarkdown, choice: LanguageChoice) -> str:
    """The guide as `cstudy learn` prints it: each example with variants in the language shown,
    with its output, then a line that names its other languages."""
    hidden: set[int] = set()
    notes: dict[int, str] = {}
    for group in example_groups(markdown):
        shown = shown_language(group.languages, choice.chosen, choice.default_language)
        kept = next(variant for variant in group.variants if variant.language == shown)
        hidden.update(range(group.start, group.end + 1))
        hidden.difference_update(range(kept.fence.start, kept.output.end + 1))
        others = ", ".join(language for language in group.languages if language != shown)
        notes[group.end] = f"Also in {others}: {choice.others_hint}".rstrip()
    return markdown.terminal_text(hidden, notes)


def _variant_at(markdown: GuideMarkdown, index: int) -> ExampleVariant | None:
    """The example block at `index` of the fences, when its output block follows it with nothing
    but blank lines between."""
    fences = markdown.fences
    fence = fences[index]
    if fence.language in (OUTPUT, PSEUDOCODE) or example_language(fence.argument or "") is None:
        return None
    if not fence.argument or not fence.argument.startswith(EXAMPLES_PREFIX):
        return None
    following = fences[index + 1] if index + 1 < len(fences) else None
    if (
        following is None
        or following.language != OUTPUT
        or following.argument != fence.argument
        or not (fence.closed and following.closed)
        or not markdown.only_blank_between(fence.end, following.start)
    ):
        return None
    return ExampleVariant(fence, following)


def _continues(markdown: GuideMarkdown, previous: ExampleVariant, variant: ExampleVariant) -> bool:
    return stem(previous.name) == stem(variant.name) and markdown.only_blank_between(
        previous.output.end, variant.fence.start
    )


def _close(run: list[ExampleVariant], groups: list[ExampleGroup]) -> None:
    if len(run) >= _MINIMUM_VARIANTS:
        groups.append(ExampleGroup(tuple(run)))
    run.clear()
