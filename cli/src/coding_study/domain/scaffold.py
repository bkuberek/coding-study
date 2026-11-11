"""What `cstudy new` writes (docs/specs/cli.md#cstudy-new): a draft problem from a template, which
a project template's `--virtual-clock` and `--stress` variants replace files of.

Template files hold `{{name}}` placeholders (`Scaffold.placeholders`); everything else in them
is literal, including the `TODO` text that `cstudy verify --static` rejects in problem.md until
the author replaces it.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain import project_tests
from coding_study.domain.concurrency import ALLOWED_MODELS, ConcurrencyModel
from coding_study.domain.errors import UsageError
from coding_study.domain.labels import Labels
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.rubric import LLD_RUBRIC_SECTIONS, rubric_skeleton
from coding_study.domain.taxonomy import PATTERNS, Scope
from coding_study.domain.virtual_clock import CLOCK_LANGUAGES, GRADED_CLOCK_LANGUAGES

ID_DIGITS = 4
WORKSPACE_FIRST_ID = 5001
"""The first id of a problem `cstudy new` writes into a workspace, above any catalog id."""
SLUG_PATTERN = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
DEFAULT_DIFFICULTY = Difficulty.MEDIUM
PROBLEM_TRACKS = (Track.DSA, Track.PRACTICAL, Track.LLD, Track.CONCURRENCY, Track.DEBUGGING)
"""Autograded tracks, whose content lives in problems/ (docs/specs/content.md#tracks)."""
_PLACEHOLDER = re.compile(r"\{\{(?P<name>[a-z_]+)\}\}")


class TemplateName(StrEnum):
    ARRAY = "array"
    TREE = "tree"
    DESIGN = "design"
    PROGRESSIVE = "progressive"
    CONCURRENT = "concurrent"
    PROJECT_PYTHON = "project-python"
    """A project problem in Python: a starter folder and the reference's overlay on it."""
    PROJECT_TYPESCRIPT = "project-typescript"
    """A project problem in TypeScript: a starter folder and the reference's overlay on it."""
    PROJECT_JAVA = "project-java"
    """A project problem in Java: a Gradle project folder and the reference's overlay on it."""
    PROJECT_KOTLIN = "project-kotlin"
    """A project problem in Kotlin: a Gradle project folder and the reference's overlay on it."""
    PROJECT_GO = "project-go"
    """A project problem in Go: a starter module and the reference's overlay on it."""
    PROJECT_RUST = "project-rust"
    """A project problem in Rust: a starter crate and the reference's overlay on it."""
    PROJECT_TYPESCRIPT_SERVICE = "project-typescript-service"
    """A service project in TypeScript: a running app in the sandbox, with a lock file."""
    PROJECT_PYTHON_SERVICE = "project-python-service"
    """A service project in Python: a running app in the sandbox, with a lock file."""
    PROJECT_JAVA_SERVICE = "project-java-service"
    """A service project in Java: a Gradle build in the sandbox, with Gradle's verification file
    as its lock."""
    PROJECT_KOTLIN_SERVICE = "project-kotlin-service"
    """A service project in Kotlin: a Gradle build in the sandbox, with Gradle's verification file
    as its lock."""
    PROJECT_GO_SERVICE = "project-go-service"
    """A service project in Go: a module on `net/http` in the sandbox, with `go.sum` as its lock."""


PROJECT_TEMPLATE_LANGUAGES: Mapping[TemplateName, Language] = {
    TemplateName.PROJECT_PYTHON: Language.PYTHON,
    TemplateName.PROJECT_TYPESCRIPT: Language.TYPESCRIPT,
    TemplateName.PROJECT_JAVA: Language.JAVA,
    TemplateName.PROJECT_KOTLIN: Language.KOTLIN,
    TemplateName.PROJECT_GO: Language.GO,
    TemplateName.PROJECT_RUST: Language.RUST,
    TemplateName.PROJECT_TYPESCRIPT_SERVICE: Language.TYPESCRIPT,
    TemplateName.PROJECT_PYTHON_SERVICE: Language.PYTHON,
    TemplateName.PROJECT_JAVA_SERVICE: Language.JAVA,
    TemplateName.PROJECT_KOTLIN_SERVICE: Language.KOTLIN,
    TemplateName.PROJECT_GO_SERVICE: Language.GO,
}
"""The one language of each project template."""
SERVICE_TEMPLATES = frozenset(
    {
        TemplateName.PROJECT_TYPESCRIPT_SERVICE,
        TemplateName.PROJECT_PYTHON_SERVICE,
        TemplateName.PROJECT_JAVA_SERVICE,
        TemplateName.PROJECT_KOTLIN_SERVICE,
        TemplateName.PROJECT_GO_SERVICE,
    }
)
"""Judged over HTTP on the real clock, so `--virtual-clock` and `--stress` do not apply."""
CLOCK_TEMPLATE_SUFFIX = "-clock"
"""A project template's virtual-clock variant is a template directory of its own, named after the
template with this suffix; `--from-template` never names it."""
STRESS_TEMPLATE_SUFFIX = "-stress"
"""`--stress` lays a directory of changed files over the template it applies to (the base template,
or its virtual-clock variant), named after that template with this suffix. Only what a stress
problem changes lives there, so the build files that check S15 compares byte for byte exist once,
in the template underneath."""


@dataclass(frozen=True, slots=True)
class TemplateDefaults:
    track: Track
    pattern: str | None
    labels: Labels


_ALGORITHMS = Labels(("algorithms",), ("general",), Scope.FUNCTION)
_BACKEND_FUNCTION = Labels(("backend",), ("backend",), Scope.FUNCTION)
_BACKEND_PROJECT = Labels(("backend",), ("backend",), Scope.PROJECT)
TEMPLATE_DEFAULTS: Mapping[TemplateName, TemplateDefaults] = {
    TemplateName.ARRAY: TemplateDefaults(Track.DSA, "arrays-hashing", _ALGORITHMS),
    TemplateName.TREE: TemplateDefaults(Track.DSA, "trees", _ALGORITHMS),
    TemplateName.DESIGN: TemplateDefaults(Track.DSA, "arrays-hashing", _ALGORITHMS),
    TemplateName.PROGRESSIVE: TemplateDefaults(Track.PRACTICAL, None, _BACKEND_FUNCTION),
    TemplateName.CONCURRENT: TemplateDefaults(
        Track.CONCURRENCY, None, Labels(("backend",), ("backend", "platform"), Scope.FUNCTION)
    ),
    **{
        template: TemplateDefaults(Track.PRACTICAL, None, _BACKEND_PROJECT)
        for template in PROJECT_TEMPLATE_LANGUAGES
    },
}
"""What `cstudy new` writes when the request leaves it out. An author edits the labels to fit the
problem, and check S24 requires them in the catalog."""


@dataclass(frozen=True, slots=True)
class ScaffoldRequest:
    slug: str
    template: TemplateName = TemplateName.ARRAY
    track: Track | None = None
    """None: the template's track."""
    title: str | None = None
    """None: from the slug, `two-sum` becomes `Two Sum`."""
    difficulty: Difficulty | None = None
    pattern: str | None = None
    """The primary pattern; None: the template's pattern, if any."""
    virtual_clock: bool = False
    """`--virtual-clock`: the project template's variant for code that waits
    (docs/decisions/0017-async-project-problems.md)."""
    stress: bool = False
    """`--stress`: a `concurrency` block, a stress case at level 2 and a broken overlay, for code
    that several threads or tasks share."""


@dataclass(frozen=True, slots=True)
class Scaffold:
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    track: Track
    patterns: tuple[str, ...]
    labels: Labels

    @property
    def directory_name(self) -> str:
        return f"{self.id}-{self.slug}"

    def placeholders(self) -> Mapping[str, str]:
        words = self.slug.split("-")
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "title_yaml": json.dumps(self.title),
            "difficulty": self.difficulty.value,
            "track": self.track.value,
            "patterns": f"patterns: [{', '.join(self.patterns)}]" if self.patterns else "",
            "labels": _labels_text(self.labels),
            "function_name": words[0] + "".join(word.capitalize() for word in words[1:]),
            "class_name": "".join(word.capitalize() for word in words),
            "crate_name": "_".join(words),
        }

    def track_files(self) -> Mapping[str, str]:
        """Files the track needs beyond the template's: `rubric.md` for `lld` (check S8)."""
        if self.track is Track.LLD:
            return {RUBRIC_FILE: rubric_skeleton(self.title, LLD_RUBRIC_SECTIONS)}
        return {}


def plan_scaffold(request: ScaffoldRequest, problem_id: str) -> Scaffold:
    """Raises UsageError for an invalid slug, title, track or pattern, and for `--virtual-clock`
    or `--stress` on a template that has no such variant."""
    template_directories(request)
    if not SLUG_PATTERN.fullmatch(request.slug):
        raise UsageError(
            f'invalid slug "{request.slug}": use lowercase words joined by "-", e.g. two-sum'
        )
    defaults = TEMPLATE_DEFAULTS[request.template]
    track = request.track or defaults.track
    if track not in PROBLEM_TRACKS:
        names = ", ".join(PROBLEM_TRACKS)
        raise UsageError(f"cstudy new scaffolds autograded problems; use a track from {names}")
    return Scaffold(
        id=problem_id,
        slug=request.slug,
        title=_title(request),
        difficulty=request.difficulty or DEFAULT_DIFFICULTY,
        track=track,
        patterns=_patterns(request.pattern or defaults.pattern, track),
        labels=defaults.labels,
    )


def template_directories(request: ScaffoldRequest) -> tuple[str, ...]:
    """The packaged templates the request writes, in the order they are laid down: a file of a
    later directory replaces the same path of an earlier one. The template's own, or its
    virtual-clock variant, then for `--stress` the directory of what a stress problem changes.

    Raises UsageError for `--virtual-clock` on a template of another kind, in a language without
    a virtual clock, or whose runner does not grade it or whose generated tests do not express it
    yet: the variant's examples hold harness operations. And for `--stress` on a template of
    another kind, or in TypeScript without the virtual clock.
    """
    if request.template in SERVICE_TEMPLATES and (request.virtual_clock or request.stress):
        raise UsageError(
            f"--virtual-clock and --stress do not apply to {request.template}: a service project "
            "runs on the real clock and is judged over HTTP"
        )
    directory = _variant_directory(request)
    if not request.stress:
        return (directory,)
    template = request.template
    language = PROJECT_TEMPLATE_LANGUAGES.get(template)
    if language is None:
        raise UsageError(f"--stress applies to the project-* templates, not {template}")
    if not request.virtual_clock and _only_runs_async(language):
        raise UsageError(
            f"--stress is not available for {template} without --virtual-clock: its stress cases "
            f"run in the {ConcurrencyModel.ASYNC} model, where only an asynchronous method can be "
            "interrupted, and asynchronous methods need the virtual clock"
        )
    return (directory, f"{directory}{STRESS_TEMPLATE_SUFFIX}")


def _only_runs_async(language: Language) -> bool:
    """Whether the async model is the language's only one, so a synchronous method runs to its end
    before another task starts and no stress case can interrupt it."""
    return ALLOWED_MODELS[language] == frozenset({ConcurrencyModel.ASYNC})


def _variant_directory(request: ScaffoldRequest) -> str:
    template = request.template
    if not request.virtual_clock:
        return template
    language = PROJECT_TEMPLATE_LANGUAGES.get(template)
    if language is None:
        raise UsageError(f"--virtual-clock applies to the project-* templates, not {template}")
    if language not in CLOCK_LANGUAGES:
        raise UsageError(
            f"--virtual-clock is not available for {template}: "
            f"{language.title()} has no virtual clock"
        )
    if language not in GRADED_CLOCK_LANGUAGES:
        raise UsageError(
            f"--virtual-clock is not available for {template} yet: "
            f"the {language} runner does not grade the virtual clock"
        )
    if language not in project_tests.HARNESS_TEST_LANGUAGES:
        raise UsageError(
            f"--virtual-clock is not available for {template} yet: "
            f"cstudy does not write {language} tests on the virtual clock"
        )
    return f"{template}{CLOCK_TEMPLATE_SUFFIX}"


def next_problem_id(directory_names: Sequence[str], first_id: int = 1) -> str:
    """The highest `<id>-` prefix plus one, zero-padded, and at least `first_id`."""
    ids = [
        int(prefix)
        for name in directory_names
        if (prefix := name.partition("-")[0]).isdigit() and len(prefix) == ID_DIGITS
    ]
    return f"{max(max(ids, default=0) + 1, first_id):0{ID_DIGITS}d}"


def render_template(text: str, placeholders: Mapping[str, str]) -> str:
    """Replaces every `{{name}}`; a line holding only a placeholder that renders empty is
    dropped. Raises KeyError for an unknown placeholder."""
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        rendered = _PLACEHOLDER.sub(lambda match: placeholders[match["name"]], line)
        if _PLACEHOLDER.search(line) and not rendered.strip():
            continue
        lines.append(rendered)
    return "".join(lines)


def _title(request: ScaffoldRequest) -> str:
    if request.title is None:
        return " ".join(word.capitalize() for word in request.slug.split("-"))
    if not request.title.strip():
        raise UsageError("--title must not be blank")
    return request.title.strip()


def _patterns(pattern: str | None, track: Track) -> tuple[str, ...]:
    if pattern is None:
        if track is Track.DSA:
            raise UsageError("track dsa needs a primary pattern: add --pattern")
        return ()
    if pattern not in PATTERNS:
        raise UsageError(f'unknown pattern "{pattern}"; see docs/specs/content.md')
    return (pattern,)


def _labels_text(labels: Labels) -> str:
    """The `domains`, `job_roles` and `scope` lines of a `meta.yaml`."""
    return (
        f"domains: [{', '.join(labels.domains)}]\n"
        f"job_roles: [{', '.join(labels.job_roles)}]\n"
        f"scope: {labels.scope}"
    )
