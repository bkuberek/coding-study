"""The options of a run or a job (docs/specs/web-ui.md#run-options, docs/specs/web-ui.md#jobs),
checked by name and type, and the `cstudy` arguments they become, built here and never by a
shell. A wrong name, type or range is a usage error, 422 `usage`; a value the command itself
refuses reaches the page from the child, as its exit code in `closed`.

A value from the request becomes an `--option=value` token, so it never reads as another option.
"""

import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from coding_study.application.run_checks import RunCheck, RunCommand, RunSubject
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language, ProblemKind

MAX_STRESS = 100
MAX_REPS = 50
END_OF_OPTIONS = "--"
RUN_FIELDS = (
    "attempt_id",
    "command",
    "level",
    "cases",
    "typecheck",
    "stress",
    "seed",
    "time_limit",
    "perf",
)
TEST_ONLY_FIELDS = ("cases", "typecheck", "stress", "seed", "time_limit", "perf")
_STRINGS = "a list of non-empty strings"


class JobCommand(StrEnum):
    DOCTOR_FIX = "doctor_fix"
    VERIFY = "verify"
    BENCH = "bench"


@dataclass(frozen=True, slots=True)
class RunOptions:
    check: RunCheck
    cases: tuple[str, ...] = ()
    typecheck: bool | None = None
    """None: the `typecheck` preference."""
    stress: int | None = None
    seed: int | None = None
    time_limit: bool | str | None = None
    """None: the configuration's; True or False: `--time-limit`, `--no-time-limit`."""
    perf: bool = False

    def document(self) -> dict[str, JsonValue]:
        """The options as `GET /api/v1/runs/{id}` shows them."""
        return {
            "level": self.check.level,
            "cases": [*self.cases],
            "typecheck": self.typecheck,
            "stress": self.stress,
            "seed": self.seed,
            "time_limit": self.time_limit,
            "perf": self.perf,
        }

    def arguments(self, subject: RunSubject) -> tuple[str, ...]:
        """`test two-sum --lang python --events --stress=10`: no `--lang` for a project, whose
        language is its own, and `--typecheck` for TypeScript only."""
        language = () if subject.kind is ProblemKind.PROJECT else ("--lang", subject.language)
        head = (self.check.command, subject.slug, *language, "--events")
        typecheck = self.typecheck and subject.language is Language.TYPESCRIPT
        flags = (
            _valued("--level", self.check.level),
            *(f"--case={case}" for case in self.cases),
            "--typecheck" if typecheck else None,
            _valued("--stress", self.stress),
            _valued("--seed", self.seed),
            _time_limit(self.time_limit),
            "--perf" if self.perf else None,
        )
        return (*head, *(flag for flag in flags if flag is not None))


@dataclass(frozen=True, slots=True)
class JobOptions:
    command: JobCommand
    arguments: tuple[str, ...]
    """The `cstudy` arguments: `doctor --fix`."""
    title: str
    """How the server names the job when it ends: `doctor --fix`."""
    document: dict[str, JsonValue]
    confirmed: bool = False
    """`doctor_fix`: the user answered its question."""
    slugs: tuple[str, ...] = ()
    """`verify`: the problems, which must be the workspace's own."""


def run_options(document: object) -> RunOptions:
    """Raises UsageError for a name, type or range the options do not take."""
    fields = _Fields(document, RUN_FIELDS)
    command = fields.choice("command", RunCommand)
    attempt_id = fields.integer("attempt_id", low=1)
    if attempt_id is None:
        raise UsageError("attempt_id is required")
    if command is RunCommand.SUBMIT:
        fields.refuse_set(TEST_ONLY_FIELDS, "cstudy submit")
    return RunOptions(
        RunCheck(attempt_id, command, fields.integer("level", low=1)),
        cases=fields.strings("cases"),
        typecheck=fields.boolean("typecheck"),
        stress=fields.integer("stress", low=1, high=MAX_STRESS),
        seed=fields.integer("seed"),
        time_limit=fields.time_limit("time_limit"),
        perf=bool(fields.boolean("perf")),
    )


def job_options(document: object) -> JobOptions:
    """Raises UsageError for a name, type or range the job does not take."""
    command = _Fields(document, (), strict=False).choice("command", JobCommand)
    return _JOB_PARSERS[command](document)


def _doctor_fix(document: object) -> JobOptions:
    fields = _Fields(document, ("command", "confirm"))
    return JobOptions(
        JobCommand.DOCTOR_FIX,
        ("doctor", "--fix"),
        "doctor --fix",
        {},
        confirmed=bool(fields.boolean("confirm")),
    )


def _verify(document: object) -> JobOptions:
    fields = _Fields(document, ("command", "slugs", "static", "oracle", "ladder"))
    slugs = fields.strings("slugs")
    if not slugs:
        raise UsageError("slugs names no problem; verify takes one or more of your own")
    switches = {name: bool(fields.boolean(name)) for name in ("static", "oracle", "ladder")}
    flags = tuple(f"--{name}" for name, on in switches.items() if on)
    return JobOptions(
        JobCommand.VERIFY,
        ("verify", *flags, END_OF_OPTIONS, *slugs),
        f"verify {' '.join(slugs)}",
        {"slugs": [*slugs], **switches},
        slugs=slugs,
    )


def _bench(document: object) -> JobOptions:
    fields = _Fields(
        document, ("command", "slug", "language", "sizes", "reps", "refs_only", "no_memory")
    )
    slug = fields.text("slug")
    language = fields.choice("language", Language)
    sizes = fields.integers("sizes", low=1)
    reps = fields.integer("reps", low=1, high=MAX_REPS)
    refs_only = bool(fields.boolean("refs_only"))
    no_memory = bool(fields.boolean("no_memory"))
    flags = (
        f"--sizes={','.join(map(str, sizes))}" if sizes else None,
        _valued("--reps", reps),
        "--refs-only" if refs_only else None,
        "--no-memory" if no_memory else None,
    )
    return JobOptions(
        JobCommand.BENCH,
        (
            "bench",
            f"--lang={language}",
            *(flag for flag in flags if flag is not None),
            END_OF_OPTIONS,
            slug,
        ),
        f"bench {slug} · {language}",
        {
            "slug": slug,
            "language": language.value,
            "sizes": [*sizes],
            "reps": reps,
            "refs_only": refs_only,
            "no_memory": no_memory,
        },
    )


_JOB_PARSERS: Mapping[JobCommand, Callable[[object], JobOptions]] = {
    JobCommand.DOCTOR_FIX: _doctor_fix,
    JobCommand.VERIFY: _verify,
    JobCommand.BENCH: _bench,
}


def _valued(option: str, value: int | None) -> str | None:
    return None if value is None else f"{option}={value}"


def _time_limit(value: bool | str | None) -> str | None:
    match value:
        case None:
            return None
        case True:
            return "--time-limit"
        case False:
            return "--no-time-limit"
        case str():
            return f"--time-limit={value}"


class _Fields:
    """The fields of a request's JSON object, read by name and type."""

    def __init__(self, document: object, names: Collection[str], *, strict: bool = True) -> None:
        if not isinstance(document, dict):
            raise UsageError("the request body is not a JSON object")
        self._values = cast(dict[str, object], document)
        unknown = sorted(set(self._values) - set(names)) if strict else []
        if unknown:
            raise UsageError(f"unknown option {unknown[0]}; the options are {', '.join(names)}")

    def choice[Choice: StrEnum](self, name: str, choices: type[Choice]) -> Choice:
        value = self._values.get(name)
        if not isinstance(value, str) or value not in set(choices):
            raise _invalid(name, value, f"one of {', '.join(choices)}")
        return choices(value)

    def integer(self, name: str, low: int | None = None, high: int | None = None) -> int | None:
        value = self._values.get(name)
        if value is None:
            return None
        if not _is_integer(value, low, high):
            raise _invalid(name, value, _integer_range(low, high))
        return cast(int, value)

    def integers(self, name: str, low: int) -> tuple[int, ...]:
        expected = f"a list of {_integer_range(low, None)}s"
        values = self._list(name, lambda value: _is_integer(value, low, None), expected)
        return tuple(cast(list[int], values))

    def boolean(self, name: str) -> bool | None:
        value = self._values.get(name)
        if value is not None and not isinstance(value, bool):
            raise _invalid(name, value, "true or false")
        return value

    def text(self, name: str) -> str:
        value = self._values.get(name)
        if not isinstance(value, str) or not value:
            raise _invalid(name, value, "a non-empty string")
        return value

    def strings(self, name: str) -> tuple[str, ...]:
        values = self._list(name, lambda value: isinstance(value, str) and bool(value), _STRINGS)
        return tuple(cast(list[str], values))

    def _list(self, name: str, valid: Callable[[object], bool], expected: str) -> list[object]:
        """The list `name` holds, empty when absent."""
        value = self._values.get(name)
        if value is None:
            return []
        if not isinstance(value, list):
            raise _invalid(name, value, expected)
        values = cast(list[object], value)
        if not all(valid(item) for item in values):
            raise _invalid(name, values, expected)
        return values

    def time_limit(self, name: str) -> bool | str | None:
        value = self._values.get(name)
        if value is None or isinstance(value, bool) or (isinstance(value, str) and value):
            return value
        raise _invalid(name, value, 'null, true, false, or a value such as "5x" or "1500ms"')

    def refuse_set(self, names: Collection[str], command: str) -> None:
        """Raises UsageError for the first of `names` holding a value other than null, false or
        an empty list: an option `command` does not take."""
        for name in names:
            if self._values.get(name) not in (None, False, []):
                raise UsageError(f"{command} takes no {name}")


def _is_integer(value: object, low: int | None, high: int | None) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _integer_range(low: int | None, high: int | None) -> str:
    if low is not None and high is not None:
        return f"an integer from {low} to {high}"
    if low == 1:
        return "a positive integer"
    return "an integer" if low is None else f"an integer from {low}"


def _invalid(name: str, value: object, expected: str) -> UsageError:
    return UsageError(f"invalid {name} {json.dumps(value)}: use {expected}")
