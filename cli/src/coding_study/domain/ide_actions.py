"""The cstudy actions a workspace offers as IDE run configurations
(docs/specs/installation-and-workspaces.md#ide-files).

One catalog for every IDE: each renderer turns these actions into its own configurations, so an
action added here appears in VS Code and in IntelliJ alike. Every argument list is a `cstudy`
command line without its target; the tests parse each one with the real command line.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.debugging import DEFAULT_DEBUG_PORTS
from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.problem import ALL_LANGUAGES, Language

EXECUTABLE = "cstudy"
LANGUAGE_NAMES: Mapping[Language, str] = {
    Language.PYTHON: "Python",
    Language.TYPESCRIPT: "TypeScript",
    Language.JAVA: "Java",
    Language.KOTLIN: "Kotlin",
}
JVM = tuple(language for language in ALL_LANGUAGES if language in JVM_LANGUAGES)
JDWP_PORT = DEFAULT_DEBUG_PORTS[Language.JAVA]
"""The JVM listener IntelliJ's "Debug JVM (listen)" waits on; Java and Kotlin share it."""


class Scope(StrEnum):
    CURRENT_FILE = "current file"
    """The solution file in the editor, passed as the target."""
    ACTIVE_ATTEMPT = "active attempt"
    """No target: the command works on the active attempt."""

    def target(self, current_file: str) -> tuple[str, ...]:
        """The target arguments, with `current_file` the IDE's spelling of the file in the
        editor."""
        return (current_file,) if self is Scope.CURRENT_FILE else ()


BOTH_SCOPES = (Scope.CURRENT_FILE, Scope.ACTIVE_ATTEMPT)
CURRENT_FILE_ONLY = (Scope.CURRENT_FILE,)
"""For commands whose target is required."""


@dataclass(frozen=True, slots=True)
class Variant:
    label: str
    argument: str
    """A single token, so an IDE can substitute it into the command line."""


@dataclass(frozen=True, slots=True)
class Choice:
    """What an action needs to know when it runs: VS Code asks, IntelliJ has one configuration
    per variant."""

    prompt: str
    variants: tuple[Variant, ...]


@dataclass(frozen=True, slots=True)
class ProblemAction:
    """A command on one problem: on the file in the editor, or on the active attempt."""

    arguments: tuple[str, ...]
    """The command and its options, before the target."""
    scopes: tuple[Scope, ...] = BOTH_SCOPES
    choice: Choice | None = None
    languages: tuple[Language, ...] = ALL_LANGUAGES
    """The languages it means something for; its name lists them unless it is all of them."""

    @property
    def command(self) -> str:
        return self.arguments[0]

    def each_variant(self) -> tuple[Variant | None, ...]:
        """One entry per configuration an IDE without prompts needs: every variant, or None."""
        return self.choice.variants if self.choice else (None,)

    def invocation(
        self, scope: Scope, current_file: str, chosen: str | None = None
    ) -> tuple[str, ...]:
        """The arguments after `cstudy`; `chosen` is a variant's argument, or the IDE's
        placeholder for the one picked when the action runs."""
        return (*self._options(chosen), *scope.target(current_file))

    def name(self, scope: Scope, variant: Variant | None = None) -> str:
        arguments = " ".join(self._options(variant.argument if variant else None))
        return f"{EXECUTABLE} {arguments} ({self._qualifier(scope)})"

    def _options(self, chosen: str | None) -> tuple[str, ...]:
        return (*self.arguments, chosen) if chosen else self.arguments

    def _qualifier(self, scope: Scope) -> str:
        if self.languages == ALL_LANGUAGES:
            return str(scope)
        return f"{scope}, {language_names(self.languages)}"


@dataclass(frozen=True, slots=True)
class WorkspaceAction:
    """A command on the whole workspace."""

    arguments: tuple[str, ...]

    @property
    def name(self) -> str:
        return f"{EXECUTABLE} {' '.join(self.arguments)}"


@dataclass(frozen=True, slots=True)
class DebugAttach:
    language: Language
    port: int
    """Where `cstudy test --debug` waits for the debugger, or connects to it, on loopback."""


def language_names(languages: tuple[Language, ...]) -> str:
    return ", ".join(LANGUAGE_NAMES[language] for language in languages)


def debug_name(scope: Scope, languages: tuple[Language, ...]) -> str:
    return f"Debug {scope} ({language_names(languages)})"


DONE_OUTCOME = Choice(
    "How did it go?",
    (
        Variant("ok", "--rating=ok"),
        Variant("easy", "--rating=easy"),
        Variant("hard", "--rating=hard"),
        Variant("gave up", "--gave-up"),
    ),
)
PROBLEM_ACTIONS = (
    ProblemAction(("test",)),
    ProblemAction(("test", "--perf")),
    ProblemAction(("test", "--typecheck"), languages=(Language.TYPESCRIPT,)),
    ProblemAction(("bench",)),
    ProblemAction(("hint",)),
    ProblemAction(("solution",), scopes=CURRENT_FILE_ONLY),
    ProblemAction(("show",), scopes=CURRENT_FILE_ONLY),
    ProblemAction(("done",), choice=DONE_OUTCOME),
    ProblemAction(("start", "--no-open"), scopes=CURRENT_FILE_ONLY),
)
"""`start` never opens an editor: the file is already open in one."""
WORKSPACE_ACTIONS = (
    WorkspaceAction(("next",)),
    WorkspaceAction(("stats",)),
    WorkspaceAction(("doctor",)),
)
DEBUG_LISTEN = ProblemAction(("test", "--debug"))
"""The runner waits on its language's port until a debugger attaches."""
DEBUG_CONNECT = ProblemAction(("test", "--debug", "--debug-connect"), languages=JVM)
"""The JVM connects to a debugger that is already listening (IntelliJ's listen mode)."""
DEBUG_ATTACH = tuple(DebugAttach(language, port) for language, port in DEFAULT_DEBUG_PORTS.items())
