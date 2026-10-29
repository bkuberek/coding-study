"""The `concurrency` block of meta.yaml (docs/specs/problem-format.md#concurrent-problems).

Each language runs stress cases in one model; the JVM languages run every stress case once per
thread kind, and each (stress case, variant) is a separate verdict.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.problem import Language

DEFAULT_RUNS = 3
VERIFY_RUNS = 10
DEFAULT_DEADLINE_MS = 5000
DEFAULT_YIELD_PROBABILITY = 0.05
DEFAULT_MAX_YIELDS = 3
STALL_GRACE_MS = 5000
"""A stress run's hang guard is its deadline plus this (docs/specs/runners.md#concurrent-jobs)."""
BROKEN_PREFIX = "broken-"
"""Broken references run as approach `broken-<id>`; approach ids may not start with it."""
JVM_LANGUAGES = frozenset({Language.JAVA, Language.KOTLIN})


class ConcurrencyModel(StrEnum):
    THREADS = "threads"
    ASYNC = "async"


class ThreadKind(StrEnum):
    PLATFORM = "platform"
    VIRTUAL = "virtual"


class PythonGranularity(StrEnum):
    LINE = "line"
    INSTRUCTION = "instruction"
    NONE = "none"


class StressVariant(StrEnum):
    """One verdict of a stress case: a JVM thread kind, or the language's only model."""

    PLATFORM = "platform"
    VIRTUAL = "virtual"
    THREAD = "thread"
    ASYNC = "async"


ALLOWED_MODELS: Mapping[Language, frozenset[ConcurrencyModel]] = {
    Language.JAVA: frozenset({ConcurrencyModel.THREADS}),
    Language.KOTLIN: frozenset({ConcurrencyModel.THREADS}),
    Language.PYTHON: frozenset({ConcurrencyModel.THREADS, ConcurrencyModel.ASYNC}),
    Language.TYPESCRIPT: frozenset({ConcurrencyModel.ASYNC}),
    Language.GO: frozenset({ConcurrencyModel.THREADS}),
    Language.RUST: frozenset({ConcurrencyModel.THREADS}),
}
"""docs/specs/problem-format.md#models-and-language-support."""


@dataclass(frozen=True, slots=True)
class Perturbation:
    yield_probability: float = DEFAULT_YIELD_PROBABILITY
    max_yields: int = DEFAULT_MAX_YIELDS
    python_granularity: PythonGranularity = PythonGranularity.LINE


@dataclass(frozen=True, slots=True)
class PerturbationOverride:
    """A stress case's `perturb`: each field set here replaces the problem's."""

    yield_probability: float | None = None
    max_yields: int | None = None
    python_granularity: PythonGranularity | None = None

    def applied_to(self, base: Perturbation) -> Perturbation:
        return Perturbation(
            base.yield_probability if self.yield_probability is None else self.yield_probability,
            base.max_yields if self.max_yields is None else self.max_yields,
            base.python_granularity if self.python_granularity is None else self.python_granularity,
        )


@dataclass(frozen=True, slots=True)
class BrokenReference:
    """A deliberately wrong reference in `solutions/broken/<id>.<ext>`."""

    id: str
    name: str
    bug: str
    caught_by: tuple[str, ...]
    """Stress case ids that must catch it."""
    languages: tuple[Language, ...] | None = None
    """None: every language of the problem."""

    @property
    def approach_id(self) -> str:
        """The id it runs and materializes under, e.g. `broken-no-lock`."""
        return f"{BROKEN_PREFIX}{self.id}"

    def covers(self, language: Language, problem_languages: tuple[Language, ...]) -> bool:
        return language in (self.languages or problem_languages)


@dataclass(frozen=True, slots=True)
class Concurrency:
    models: Mapping[Language, ConcurrencyModel]
    """The model of each language that has one; problems list only languages with a model."""
    jvm_threads: tuple[ThreadKind, ...] = (ThreadKind.PLATFORM,)
    runs: int = DEFAULT_RUNS
    deadline_ms: int = DEFAULT_DEADLINE_MS
    perturb: Perturbation = Perturbation()
    broken: tuple[BrokenReference, ...] = field(default_factory=tuple[BrokenReference, ...])

    def model_for(self, language: Language) -> ConcurrencyModel | None:
        return self.models.get(language)

    def variants(self, language: Language) -> tuple[StressVariant, ...]:
        """The verdicts every stress case has in `language`, in run order."""
        if language in JVM_LANGUAGES:
            return tuple(StressVariant(kind.value) for kind in self.jvm_threads)
        model = self.model_for(language)
        if model is ConcurrencyModel.THREADS:
            return (StressVariant.THREAD,)
        return (StressVariant.ASYNC,)

    def broken_reference(self, broken_id: str) -> BrokenReference | None:
        return next((broken for broken in self.broken if broken.id == broken_id), None)


def model_problems(concurrency: Concurrency, languages: tuple[Language, ...]) -> tuple[str, ...]:
    """Why `concurrency.model` does not fit `languages` (check S11)."""
    problems: list[str] = []
    for language in languages:
        model = concurrency.model_for(language)
        if model is None:
            problems.append(f"no model for {language}")
        elif model not in ALLOWED_MODELS[language]:
            allowed = " or ".join(sorted(ALLOWED_MODELS[language]))
            problems.append(f"{language} cannot use the {model} model (use {allowed})")
    return tuple(problems)


def thread_kinds_text(concurrency: Concurrency) -> str:
    """`platform and virtual`, as stub headers and statements name them."""
    return " and ".join(kind.value for kind in concurrency.jvm_threads)


def model_text(concurrency: Concurrency, language: Language) -> str:
    """The stub header's model, e.g. `threads (platform and virtual)` on the JVM."""
    model = concurrency.model_for(language) or ConcurrencyModel.THREADS
    if language in JVM_LANGUAGES:
        return f"{model} ({thread_kinds_text(concurrency)})"
    return model.value
