"""The selected JDK against a problem's range, at the commands that build or run Java and Kotlin
(docs/specs/cli.md#the-selected-jdk).

`start`, `test`, `submit` and `bench` refuse before they write or build anything; `verify` skips.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.domain.errors import FIX_PREFIX, RunnerStartError
from coding_study.domain.jdk import JDK_FIX
from coding_study.domain.jdk_fit import JdkFit, content_release, fit_of
from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.problem import Language, ProblemMeta


@dataclass(frozen=True, slots=True)
class JdkSplit:
    """A problem's languages, by whether the selected JDK can run them."""

    runnable: tuple[Language, ...]
    skipped: tuple[Language, ...]
    """Java and Kotlin, when the JDK is outside the problem's range."""
    reason: str | None
    """Why they are skipped; None when none is."""


def release_of_content(meta: ProblemMeta, language: Language) -> int | None:
    """The release level that what `cstudy verify` and `cstudy bench` build from the content
    compiles at (`cs.release`): the problem's minimum JDK. None for the languages that take none."""
    return content_release(meta) if language in JVM_LANGUAGES else None


def jdk_fit(environment: Environment, meta: ProblemMeta) -> JdkFit:
    """The selected JDK against the range of `meta`."""
    jdk = environment.jdk
    return fit_of(jdk.selected(), jdk.unusable_java_home(), meta.jdk)


def require_jdk(environment: Environment, meta: ProblemMeta, language: Language) -> None:
    """Raises RunnerStartError (exit 4) when `language` is Java or Kotlin and the selected JDK is
    outside the problem's range, or there is none. The other languages take no JDK."""
    if language not in JVM_LANGUAGES:
        return
    fit = jdk_fit(environment, meta)
    if not fit.runs:
        raise RunnerStartError(fit.refusal(meta.slug, language), (f"{FIX_PREFIX}{JDK_FIX}",))


def split_by_jdk(
    environment: Environment, meta: ProblemMeta, languages: Sequence[Language]
) -> JdkSplit:
    """`languages` in their order, with Java and Kotlin moved to `skipped` when the selected JDK
    cannot run them."""
    fit = jdk_fit(environment, meta)
    if fit.runs:
        return JdkSplit(tuple(languages), (), None)
    runnable = tuple(language for language in languages if language not in JVM_LANGUAGES)
    skipped = tuple(language for language in languages if language in JVM_LANGUAGES)
    return JdkSplit(runnable, skipped, fit.skip_reason() if skipped else None)
