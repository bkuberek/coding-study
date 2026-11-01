"""The JDK range cstudy supports and the range a problem declares
(docs/decisions/0016-jdk-range.md, docs/specs/problem-format.md#jdk-range).

The supported range is also defined in `runners/jvm/gradle/libs.versions.toml`, where Gradle
reads it; a test keeps the two equal, since neither side can read the other without a file read in
the domain or a generator across languages.
"""

from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.guides import TOOLCHAINS_GUIDE


@dataclass(frozen=True, slots=True)
class JdkRange:
    """The JDK feature releases from `minimum` to `maximum`, both included."""

    minimum: int
    maximum: int

    def contains(self, feature: int) -> bool:
        return self.minimum <= feature <= self.maximum


SUPPORTED_JDKS = JdkRange(minimum=21, maximum=26)
"""What cstudy runs Java and Kotlin on. 21 is the first release with final virtual threads, and
26 the newest one the pinned Kotlin can target. The tested ends are 21 and 26."""

RECOMMENDED_JDK = 25
"""The newest long-term-support release in the range: the one the toolchains guide and the fix
name, though any JDK in the range works."""

JAVA_HOME_VARIABLE = "JAVA_HOME"
GRADLE_JAVA_HOME_ARGUMENT = "-Dorg.gradle.java.home="
"""Outranks `org.gradle.java.home` in the user's Gradle home, which `JAVA_HOME` does not."""

JDK_FIX = (
    f"select a JDK {SUPPORTED_JDKS.minimum} to {SUPPORTED_JDKS.maximum} with JAVA_HOME, "
    f"or install JDK {RECOMMENDED_JDK}: {TOOLCHAINS_GUIDE}#jdk"
)
"""What to do when the selected JDK cannot run Java and Kotlin, or there is none."""


@dataclass(frozen=True, slots=True)
class DeclaredJdk:
    """The `jdk` field of meta.yaml, as written. A missing bound is the bound of the supported
    range, so a problem follows the range when it grows."""

    minimum: int | None = None
    maximum: int | None = None


def effective_range(declared: DeclaredJdk | None, supported: JdkRange = SUPPORTED_JDKS) -> JdkRange:
    """A problem's range: its explicit bounds, with a missing one taken from the supported range."""
    if declared is None:
        return supported
    return JdkRange(
        minimum=supported.minimum if declared.minimum is None else declared.minimum,
        maximum=supported.maximum if declared.maximum is None else declared.maximum,
    )


class JdkSource(StrEnum):
    """Where the selected JDK came from: the Gradle wrapper's own rule."""

    JAVA_HOME = "JAVA_HOME"
    PATH = "PATH"


@dataclass(frozen=True, slots=True)
class SelectedJdk:
    """The one JDK a command builds and runs with: the one the shell selects."""

    version: str
    """As the JDK's `release` file spells it, such as `26.0.1`."""
    feature: int
    source: JdkSource

    @property
    def supported(self) -> bool:
        return SUPPORTED_JDKS.contains(self.feature)


def no_jdk_sentence(java_home: str | None) -> str:
    """Why nothing is selected: a `JAVA_HOME` that holds no JDK, which the selection does not look
    past, or no JDK at all."""
    if java_home is None:
        return "no JDK was found"
    return f"JAVA_HOME ({java_home}) holds no JDK"


class JdkAvailability(StrEnum):
    """Whether the selected JDK can run a problem's Java and Kotlin, and if not, why."""

    AVAILABLE = "available"
    NO_JDK = "no-jdk"
    TOO_OLD = "too-old"
    NOT_SUPPORTED_YET = "not-supported-yet"
    NEWER_THAN_THE_PROBLEM = "newer-than-the-problem"


def availability(
    selected: SelectedJdk | None, wanted: JdkRange, supported: JdkRange = SUPPORTED_JDKS
) -> JdkAvailability:
    """`wanted` is the problem's effective range. No JDK at all is outside every range."""
    if selected is None:
        return JdkAvailability.NO_JDK
    if selected.feature < wanted.minimum:
        return JdkAvailability.TOO_OLD
    if selected.feature <= wanted.maximum:
        return JdkAvailability.AVAILABLE
    if wanted.maximum < supported.maximum:
        return JdkAvailability.NEWER_THAN_THE_PROBLEM
    return JdkAvailability.NOT_SUPPORTED_YET


@dataclass(frozen=True, slots=True)
class JdkIssue:
    location: str
    message: str


def bound_issues(
    declared: DeclaredJdk, supported: JdkRange = SUPPORTED_JDKS
) -> tuple[JdkIssue, ...]:
    """Check S17 on the bounds. `min` is above the supported minimum, which a missing one already
    means, and at most the supported maximum, which caps every level. `max` is at least the
    effective minimum and not the supported maximum: an explicit one would keep the problem from
    following the range when it grows. A `max` above the supported maximum is an opt-in."""
    return (
        *_minimum_issues(declared.minimum, supported),
        *_maximum_issues(declared, supported),
    )


def _minimum_issues(minimum: int | None, supported: JdkRange) -> tuple[JdkIssue, ...]:
    if minimum is None:
        return ()
    if minimum <= supported.minimum:
        message = (
            f"{minimum} is not above the supported minimum {supported.minimum}, "
            "which a missing min already means"
        )
        return (JdkIssue("jdk.min", message),)
    if minimum > supported.maximum:
        message = f"{minimum} is above the supported maximum {supported.maximum}"
        return (JdkIssue("jdk.min", message),)
    return ()


def _maximum_issues(declared: DeclaredJdk, supported: JdkRange) -> tuple[JdkIssue, ...]:
    maximum = declared.maximum
    if maximum is None:
        return ()
    issues: list[JdkIssue] = []
    minimum = effective_range(declared, supported).minimum
    if maximum < minimum:
        issues.append(JdkIssue("jdk.max", f"{maximum} is below the minimum {minimum}"))
    if maximum == supported.maximum:
        message = (
            f"{maximum} is the supported maximum: leave it out, "
            "so that the problem follows the range when it grows"
        )
        issues.append(JdkIssue("jdk.max", message))
    return tuple(issues)
