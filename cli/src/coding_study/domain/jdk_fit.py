"""Whether the selected JDK can run a problem's Java and Kotlin, and the words for when it cannot
(docs/specs/cli.md#the-selected-jdk, docs/decisions/0016-jdk-range.md)."""

from dataclasses import dataclass

from coding_study.domain.jdk import (
    SUPPORTED_JDKS,
    DeclaredJdk,
    JdkAvailability,
    JdkRange,
    SelectedJdk,
    availability,
    effective_range,
    no_jdk_sentence,
)
from coding_study.domain.problem import Language, ProblemMeta

_WHY_NOT_RUN = {
    JdkAvailability.NOT_SUPPORTED_YET: "which cstudy does not support yet",
    JdkAvailability.NEWER_THAN_THE_PROBLEM: "which is newer than the problem supports",
    JdkAvailability.TOO_OLD: "which is too old",
}


def range_text(wanted: JdkRange) -> str:
    """`JDK 21 to 26`, or `JDK 24` for a range of one release."""
    if wanted.minimum == wanted.maximum:
        return f"JDK {wanted.minimum}"
    return f"JDK {wanted.minimum} to {wanted.maximum}"


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

    def skip_reason(self) -> str:
        """Why `cstudy verify` skips the problem's Java and Kotlin."""
        return f"runs on {range_text(self.wanted)}; {self._selection()}"

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


def content_release(meta: ProblemMeta) -> int:
    """The release level that the references, stubs and starters of `meta` compile at: its
    minimum JDK (docs/specs/runners.md#the-jdk-and-the-release-level)."""
    return effective_range(meta.jdk).minimum
