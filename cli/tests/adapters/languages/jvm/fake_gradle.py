"""A stand-in for the Gradle wrapper and reference sources, shared by the JVM runner tests."""

import shutil
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from coding_study.adapters.languages.jvm.gradle import GradleOutcome
from coding_study.application.ports import ReferenceSource
from coding_study.domain.problem import Language

CLASSPATH = "/classes:/runner.jar"
WORKSPACE_FILES = (
    "gradle.properties",
    "gradle/libs.versions.toml",
    "java/build.gradle.kts",
    "kotlin/build.gradle.kts",
)
CLASS_DIRECTORIES = {Language.JAVA: "classes/java/main", Language.KOTLIN: "classes/kotlin/main"}
CLASS_FILE = "Solution.class"
JAVA_SOURCE = "public class Solution {\n}\n"
KOTLIN_SOURCE = "class Solution\n"
ONLY_PROPERTY = "-Pcs.only="


class FakeGradle:
    """Records every build; a successful build writes the classpath file like `csClasspath`."""

    def __init__(self, root: Path, *, warm: bool = True, outcome: GradleOutcome | None = None):
        self.root = root
        self.warm = warm
        self.outcome = outcome or GradleOutcome(0, "")
        self.builds: list[tuple[str, ...]] = []

    def daemon_running(self) -> bool:
        return self.warm

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        self.builds.append(tuple(arguments))
        if self.outcome.exit_code == 0:
            project = self.project_directory(arguments)
            task_project = next(arg for arg in arguments if arg.endswith(":csClasspath"))
            language = Language(task_project.split(":")[1])
            only = next(arg for arg in arguments if arg.startswith(ONLY_PROPERTY))
            classpath = self.build_classes(project, language, only.removeprefix(ONLY_PROPERTY))
            output = project / language / "build" / "cs" / "runtime-classpath.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(f"{classpath}\n")
        return self.outcome

    def build_classes(self, project: Path, language: Language, slug: str) -> str:
        """Builds `slug` in `project`; returns the runtime classpath."""
        return CLASSPATH

    def project_directory(self, arguments: Sequence[str]) -> Path:
        if "-p" in arguments:
            return Path(arguments[list(arguments).index("-p") + 1])
        return self.root / "jvm"


class ClassBuildingGradle(FakeGradle):
    """Builds like Gradle with `-Pcs.only`: the output directory keeps the class of the requested
    problem only, and it is on the runtime classpath next to a jar.

    `pause` stretches each build, so builds that overlap are noticed; `on_build` runs inside it.
    """

    def __init__(
        self,
        root: Path,
        *,
        pause: float = 0.0,
        on_build: Callable[[], object] = lambda: None,
        outcome: GradleOutcome | None = None,
    ):
        super().__init__(root, outcome=outcome)
        self._pause = pause
        self._on_build = on_build
        self._guard = threading.Lock()
        self._running = 0
        self.most_running = 0

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        with self._guard:
            self._running += 1
            self.most_running = max(self.most_running, self._running)
        try:
            self._on_build()
            time.sleep(self._pause)
            return super().run(arguments)
        finally:
            with self._guard:
                self._running -= 1

    def build_classes(self, project: Path, language: Language, slug: str) -> str:
        output = project / language / "build" / CLASS_DIRECTORIES[language]
        shutil.rmtree(output, ignore_errors=True)
        (output / slug).mkdir(parents=True)
        (output / slug / CLASS_FILE).write_text(slug)
        return f"{output}:/runner.jar"


PROJECT_CLASSPATH_FILES = {
    "csClasspath": ("build/cs/main-classpath.txt", "build/cs/test-classpath.txt"),
    "csMainClasspath": ("build/cs/main-classpath.txt",),
}
"""What each task of the `cs.project` plugin writes, relative to the project folder."""


class ProjectGradle:
    """Builds a project folder like the `cs.project` plugin: the main classes, the test classes
    with `csClasspath`, and the classpath files naming them next to a library jar.

    `pause` stretches each build so that builds that overlap are noticed.
    """

    def __init__(
        self, *, warm: bool = True, outcome: GradleOutcome | None = None, pause: float = 0.0
    ):
        self.warm = warm
        self.outcome = outcome or GradleOutcome(0, "")
        self.builds: list[tuple[str, ...]] = []
        self._pause = pause
        self._guard = threading.Lock()
        self._running = 0
        self.most_running = 0

    def daemon_running(self) -> bool:
        return self.warm

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        with self._guard:
            self.builds.append(tuple(arguments))
            self._running += 1
            self.most_running = max(self.most_running, self._running)
        try:
            time.sleep(self._pause)
            if self.outcome.exit_code == 0:
                self._build(Path(arguments[list(arguments).index("-p") + 1]), arguments)
            return self.outcome
        finally:
            with self._guard:
                self._running -= 1

    def _build(self, root: Path, arguments: Sequence[str]) -> None:
        task = next(argument for argument in arguments if argument in PROJECT_CLASSPATH_FILES)
        main = root / "build" / "classes" / "java" / "main"
        test = root / "build" / "classes" / "java" / "test"
        for directory, name in ((main, "Bank.class"), (test, "Level1Test.class")):
            (directory / "bank").mkdir(parents=True, exist_ok=True)
            (directory / "bank" / name).write_text(name)
        classpaths = {
            "main-classpath.txt": f"{main}:{LIBRARY}",
            "test-classpath.txt": f"{test}:{main}:{LIBRARY}",
        }
        for relative in PROJECT_CLASSPATH_FILES[task]:
            output = root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(f"{classpaths[output.name]}\n")


LIBRARY = "/gradle/caches/junit-jupiter.jar"
"""A jar in Gradle's cache: a run keeps its path, as nothing rewrites it."""


def reference_sources(
    directory: Path, language: Language, *approaches: str
) -> tuple[ReferenceSource, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    extension = "java" if language is Language.JAVA else "kt"
    text = JAVA_SOURCE if language is Language.JAVA else KOTLIN_SOURCE
    sources = []
    for approach in approaches:
        path = directory / f"{approach}.{extension}"
        path.write_text(text)
        sources.append(ReferenceSource(approach, path))
    return tuple(sources)
