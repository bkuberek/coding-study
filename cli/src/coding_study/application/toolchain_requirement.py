"""The languages that can run here, at the commands that run every language of a problem
(docs/specs/cli.md#cstudy-verify).

A language whose toolchain is missing is skipped with the reason, as Java and Kotlin are when the
selected JDK is outside the problem's range (`coding_study.application.jdk_requirement`), so one
missing program does not stop the others from being verified. A service project runs in Docker, so
only the JDK range applies to it, not the programs of the host.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.jdk_requirement import split_by_jdk
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.service_project import service_of


@dataclass(frozen=True, slots=True)
class ToolchainSplit:
    """A problem's languages, by whether their toolchains can run them."""

    runnable: tuple[Language, ...]
    skipped: tuple[Language, ...]
    """Without the JDK of its range, or without `node`, `go`, `cargo` or the Python workspace."""
    reasons: Mapping[Language, str]
    """Why each skipped language is skipped."""

    def reason_groups(self) -> tuple[tuple[tuple[Language, ...], str], ...]:
        """The skipped languages that share a reason, in the order of their first appearance."""
        distinct = dict.fromkeys(self.reasons[language] for language in self.skipped)
        return tuple(
            (
                tuple(language for language in self.skipped if self.reasons[language] == reason),
                reason,
            )
            for reason in distinct
        )


def narrowed(
    listed: Sequence[Language], only: Language | None, skip: Collection[Language]
) -> list[Language]:
    """`listed`, in its order, narrowed to `only` (`--lang`) and without `skip` (`--skip-lang`)."""
    return [language for language in listed if only in (None, language) and language not in skip]


def split_by_toolchain(
    environment: Environment, meta: ProblemMeta, languages: Sequence[Language]
) -> ToolchainSplit:
    """`languages` in their order, with those moved to `skipped` that the selected JDK or the
    machine's toolchains cannot run. A service project's languages are judged by the JDK range
    alone: its toolchains are the ones in its Docker images."""
    jdk = split_by_jdk(environment, meta, languages)
    reasons = {language: jdk.reason for language in jdk.skipped if jdk.reason is not None}
    if service_of(meta) is not None:
        return ToolchainSplit(jdk.runnable, jdk.skipped, reasons)
    runnable: list[Language] = []
    for language in jdk.runnable:
        missing = environment.toolchain_check.missing(language)
        if missing is None:
            runnable.append(language)
        else:
            reasons[language] = missing
    skipped = tuple(language for language in languages if language in reasons)
    return ToolchainSplit(tuple(runnable), skipped, reasons)
