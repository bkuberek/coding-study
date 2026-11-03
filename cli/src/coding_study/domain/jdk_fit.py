"""Whether the selected JDK can run a problem's Java and Kotlin, and the words for when it cannot
(docs/specs/cli.md#the-selected-jdk, docs/decisions/0016-jdk-range.md)."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from coding_study.domain.jdk import (
    SUPPORTED_JDKS,
    DeclaredJdk,
    JdkAvailability,
    JdkRange,
    SelectedJdk,
    availability,
    effective_range,
    jdk_fix,
    no_jdk_sentence,
    range_text,
)
from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.problem import Language, ProblemMeta

_WHY_NOT_RUN = {
    JdkAvailability.NOT_SUPPORTED_YET: "which cstudy does not support yet",
    JdkAvailability.NEWER_THAN_THE_PROBLEM: "which is newer than the problem supports",
    JdkAvailability.TOO_OLD: "which is too old",
}


def selection_text(selected: SelectedJdk) -> str:
    """`JAVA_HOME selects JDK 27`: where the JDK came from, and its feature release."""
    return f"{selected.source} selects JDK {selected.feature}"


@dataclass(frozen=True, slots=True)
class JdkFit:
    """The selected JDK against one problem's range."""

    wanted: JdkRange
    """The problem's effective range."""
    selected: SelectedJdk | None
    unusable_java_home: str | None
    """`JAVA_HOME` as it is set, when it holds no JDK."""

    @property
    def availability(self) -> JdkAvailability:
        return availability(self.selected, self.wanted)

    @property
    def runs(self) -> bool:
        return self.availability is JdkAvailability.AVAILABLE

    def refusal(self, slug: str, language: Language) -> str:
        """Why `cstudy start`, `test`, `submit` or `bench` refuses `slug` in `language`."""
        return f"{slug} runs its {language} version on {range_text(self.wanted)}; {self._why()}"

    @property
    def fix(self) -> str:
        """How to select a JDK that runs the problem."""
        return jdk_fix(self.wanted)

    def skip_reason(self) -> str:
        """Why `cstudy verify` skips the problem's Java and Kotlin."""
        return f"runs on {range_text(self.wanted)}; {self._selection()}"

    def blocked(self, languages: Iterable[Language]) -> tuple[Language, ...]:
        """The Java and Kotlin among `languages`, when the JDK cannot run the problem."""
        if self.runs:
            return ()
        return tuple(language for language in languages if language in JVM_LANGUAGES)

    def _why(self) -> str:
        selected = self.selected
        if selected is None:
            return self._selection()
        return f"{selection_text(selected)}, {_WHY_NOT_RUN[self.availability]}"

    def _selection(self) -> str:
        if self.selected is None:
            return no_jdk_sentence(self.unusable_java_home)
        return selection_text(self.selected)


def fit_of(
    selected: SelectedJdk | None,
    unusable_java_home: str | None,
    declared: DeclaredJdk | None,
    supported: JdkRange = SUPPORTED_JDKS,
) -> JdkFit:
    return JdkFit(effective_range(declared, supported), selected, unusable_java_home)


def jdk_range_of(meta: ProblemMeta) -> JdkRange | None:
    """The range that `cstudy list --json` gives a problem: its effective one, or None for a
    problem that lists neither Java nor Kotlin."""
    if not JVM_LANGUAGES.intersection(meta.languages):
        return None
    return effective_range(meta.jdk)


def listing_reason(selected: SelectedJdk | None, unusable_java_home: str | None) -> str:
    """The reason in the footer of `cstudy list` for the languages it marks."""
    if selected is None:
        return no_jdk_sentence(unusable_java_home)
    where = f"not run on JDK {selected.feature} ({selected.source})"
    if selected.supported:
        return f"{where}: outside the JDK range the problem declares"
    return f"{where}: {_supports()}"


def cannot_run_text(
    selected: SelectedJdk | None, unusable_java_home: str | None, languages: Sequence[Language]
) -> str:
    """Why `cstudy next` and `cstudy mock` find no problem in `languages` that the JDK can run."""
    named = " and ".join(languages)
    if selected is None:
        none = no_jdk_sentence(unusable_java_home)
        return f"{none}, so {named} problems cannot run; {_supports()}"
    jdk = f"JDK {selected.feature} ({selected.source})"
    if selected.supported:
        return f"{jdk} is outside the JDK range of the {named} problems in scope"
    return f"{jdk} cannot run {named} problems; {_supports()}"


def _supports() -> str:
    return f"cstudy supports {range_text(SUPPORTED_JDKS)}"


_JVM_NAMES = ((Language.JAVA, "Java"), (Language.KOTLIN, "Kotlin"))


def statement_range(meta: ProblemMeta) -> str | None:
    """`Java and Kotlin: JDK 24 or newer`: the range a problem declares, for its statement's
    metadata line; None for the default range."""
    declared = meta.jdk
    if declared is None:
        return None
    names = " and ".join(name for language, name in _JVM_NAMES if language in meta.languages)
    if not names:
        return None
    minimum, maximum = declared.minimum, declared.maximum
    if minimum is not None and maximum is not None:
        return f"{names}: {range_text(JdkRange(minimum, maximum))}"
    if minimum is not None:
        return f"{names}: JDK {minimum} or newer"
    if maximum is not None:
        return f"{names}: JDK {maximum} or older"
    return None


def content_release(meta: ProblemMeta) -> int:
    """The release level that the references, stubs and starters of `meta` compile at: its
    minimum JDK (docs/specs/runners.md#the-jdk-and-the-release-level)."""
    return effective_range(meta.jdk).minimum
