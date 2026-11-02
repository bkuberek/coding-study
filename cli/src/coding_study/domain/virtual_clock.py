"""The virtual clock of project problems
(docs/specs/problem-format.md#asynchronous-code-and-the-virtual-clock).

`project.clock: virtual` puts every case of a project on a clock that moves only when every task
waits, and `async: true` marks a method that returns the language's awaitable. Both belong to the
languages whose ecosystem has a virtual time to test with (docs/decisions/0017-async-project-
problems.md): Go, Python, TypeScript, Kotlin and Rust have the clock, and all but Go have
awaitable methods, since a Go method blocks. Java has neither.

A language can declare them only once its runner grades them. The runners arrive one language
family at a time, so `GRADED_CLOCK_LANGUAGES` names the languages that did: a declaration in
another is refused with a message that says so, instead of reaching a runner that would call
`@advance` as a method.
"""

from enum import StrEnum

from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.signature import ClassSignature, SignatureIssue

CLOCK_LANGUAGES = (
    Language.GO,
    Language.PYTHON,
    Language.TYPESCRIPT,
    Language.KOTLIN,
    Language.RUST,
)
"""The languages that can declare `project.clock: virtual`."""
ASYNC_LANGUAGES = (Language.PYTHON, Language.TYPESCRIPT, Language.KOTLIN, Language.RUST)
"""The languages that can declare `async: true`: those whose methods return an awaitable."""
GRADED_CLOCK_LANGUAGES: frozenset[Language] = frozenset(
    {Language.GO, Language.PYTHON, Language.TYPESCRIPT, Language.KOTLIN}
)
"""The languages whose runner grades the virtual clock and its harness operations. Each step of
docs/decisions/0017-async-project-problems.md#scope-and-order adds its languages here, together
with the runner's `clock` feature: Go's grading binary is a test binary that runs each case in a
`testing/synctest` bubble, Python's runner runs each case on an asyncio loop of
`cs_support.virtual_clock`, TypeScript's on `node:test`'s mock timers, which
`runners/typescript/lib/virtual-clock.ts` drives, and the JVM runner a Kotlin project's on a
`kotlinx-coroutines-test` scheduler, through the bridge `cs.coroutines`."""


class ProjectClock(StrEnum):
    """The `project.clock` field; the real clock is the default and is never written."""

    VIRTUAL = "virtual"


def clock_declaration_issues(meta: ProblemMeta) -> tuple[SignatureIssue, ...]:
    """Why a project's `clock` and `async` declarations cannot hold in its language (check S18).

    Empty for a problem of another kind, whose own checks refuse `async`
    (`signature.async_issues`), and for a project that lists other than one language, which S14
    refuses.
    """
    if meta.kind is not ProblemKind.PROJECT or len(meta.languages) != 1:
        return ()
    language = meta.languages[0]
    clock = meta.project.clock if meta.project is not None else None
    issues = list(_clock_issues(clock, language))
    issues += _async_issues(meta, clock, language)
    return tuple(issues)


def _clock_issues(clock: ProjectClock | None, language: Language) -> list[SignatureIssue]:
    if clock is None:
        return []
    location = "project.clock"
    if language not in CLOCK_LANGUAGES:
        message = f'"{clock}" is for {_listing(CLOCK_LANGUAGES)} projects, not {language}'
        return [SignatureIssue(location, message)]
    if language not in GRADED_CLOCK_LANGUAGES:
        message = f"the {language} runner does not grade the virtual clock yet"
        return [SignatureIssue(location, message)]
    return []


def _async_issues(
    meta: ProblemMeta, clock: ProjectClock | None, language: Language
) -> list[SignatureIssue]:
    signature = meta.signature
    if not isinstance(signature, ClassSignature):
        return []
    issues: list[SignatureIssue] = []
    for index, method in enumerate(signature.methods):
        if not method.is_async:
            continue
        location = f"signature.class.methods[{index}].async"
        if language not in ASYNC_LANGUAGES:
            message = f"only {_listing(ASYNC_LANGUAGES)} methods can be async, not {language}'s"
            issues.append(SignatureIssue(location, message))
        elif clock is None:
            message = "needs project.clock: virtual, since a real clock would wait for real"
            issues.append(SignatureIssue(location, message))
    return issues


def _listing(languages: tuple[Language, ...]) -> str:
    *others, last = languages
    return f"{', '.join(others)} and {last}"
