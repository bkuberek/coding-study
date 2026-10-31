"""`cstudy verify --static` checks S14 to S16 on project problems (docs/specs/authoring.md#static).

S14 covers meta.yaml, the cases and the files a project problem may not have; S15 the starter and
the reference overlays; S16 the generated test names, `## Project` in problem.md and `### Design`
in the explanation. The schema refuses `stub`, `perf` and `concurrency` on a project problem,
since only it sees them at their default values. Symbolic links in the trees fail while loading
the problem, so no listed path leaves its folder.
"""

import json
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from coding_study.domain.cases import GeneratedInput
from coding_study.domain.errors import ContentIssue
from coding_study.domain.explanation import Explanation
from coding_study.domain.markdown import MarkdownDocument, MarkdownSection
from coding_study.domain.problem import ComparatorType, Language, Problem, ProblemKind, Track
from coding_study.domain.problem_files import (
    BUGGY_DIRECTORY,
    CHECKER_FILE,
    EXPLANATION_FILE,
    GENERATOR_FILE,
    META_FILE,
    PROBLEM_FILE,
    SOLUTIONS_DIRECTORY,
    STARTER_DIRECTORY,
    STRESS_CHECKER_FILE,
    TESTS_FILE,
)
from coding_study.domain.project import (
    NO_PROJECT_FILES,
    PATH_SEPARATOR,
    PROJECT_LANGUAGES,
    Project,
    ProjectFile,
    ProjectTree,
    entry_files,
    entry_issue,
    go_package_name,
    level_test_pattern,
    level_tests_directory_issue,
    relative_path_issue,
    unsupported_language,
)
from coding_study.domain.signature import declared_types
from coding_study.domain.stress import StressScenario
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    VoidType,
    scalars_of,
)
from coding_study.domain.workspace_projects import (
    GO_MODULE_FILE,
    GO_VENDORED_MODULES,
    GO_WORK_FILE,
    GO_WORK_SUM_FILE,
    GO_WORK_VERSION,
    go_module_file,
    go_vendored_replacement,
)

MAX_STARTER_FILES = 50
MAX_STARTER_KIB = 256
MAX_STARTER_BYTES = MAX_STARTER_KIB * 1024
README_FILE = "README.md"
PYPROJECT_FILE = "pyproject.toml"
PACKAGE_FILE = "package.json"
TSCONFIG_FILE = "tsconfig.json"
PROJECT_SECTION = "Project"
OUTPUT_SECTION = "Output"
DESIGN_SUBSECTION = "Design"
ALGORITHM_SUBSECTION = "Algorithm"
GENERATED_TEST_COMPARATORS = (ComparatorType.EXACT, ComparatorType.UNORDERED, ComparatorType.FLOAT)
"""What a generated test can assert."""
FORBIDDEN_FILES = (GENERATOR_FILE, CHECKER_FILE, STRESS_CHECKER_FILE)
CACHE_DIRECTORIES = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "node_modules"}
)
BUILD_OUTPUT_SUFFIXES = (".pyc", ".tsbuildinfo")
LOCK_FILES = frozenset(
    {
        *("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock"),
        *("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock"),
        *("bun.lock", "bun.lockb"),
        "go.sum",
    }
)
SHADOWED_PYTHON_MODULES = frozenset({"pytest"})
"""Besides the standard library: what a starter module would hide from the native tests."""
REQUIRES_PYTHON = "requires-python"
PACKAGE_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)
_PYTHON_SUFFIX = ".py"
_GO_MAIN_PACKAGE = "main"

type _Report = Callable[[str, str], None]
"""Reports a message on a path of the starter."""


@dataclass(frozen=True, slots=True)
class ProjectContent:
    """What S14 to S16 read from one problem directory."""

    directory: str
    problem: Problem
    problem_markdown: str | None
    explanation: str | None
    files: tuple[str, ...]
    """File names directly in the problem directory."""
    buggy_files: tuple[str, ...]
    """File names in buggy/."""


def project_issues(content: ProjectContent) -> tuple[ContentIssue, ...]:
    """S14 to S16; for any other kind, only that it has no `project` block."""
    issues = _Issues(content.directory)
    meta = content.problem.meta
    if meta.kind is not ProblemKind.PROJECT:
        if meta.project is not None:
            issues.error(META_FILE, "only project problems have one", "project")
        return tuple(issues.errors)
    _Settings(issues, content).check()
    _Trees(issues, content).check()
    _Documents(issues, content).check()
    return tuple(issues.errors)


class _Issues:
    def __init__(self, directory: str) -> None:
        self._directory = directory
        self.errors: list[ContentIssue] = []

    def error(self, name: str, message: str, location: str = "") -> None:
        self.errors.append(ContentIssue(f"{self._directory}/{name}", location, message))


def _language(content: ProjectContent) -> Language | None:
    """The problem's one language, when project problems support it."""
    languages = content.problem.meta.languages
    if len(languages) == 1 and languages[0] in PROJECT_LANGUAGES:
        return languages[0]
    return None


def _well_formed_entry(content: ProjectContent) -> tuple[Project, Language] | None:
    """The project block and the language, when the entry is well formed for it."""
    project, language = content.problem.meta.project, _language(content)
    if project is None or language is None or entry_issue(project.entry, language):
        return None
    return project, language


class _Settings:
    """S14: meta.yaml, the cases, and the files a project problem may not have."""

    def __init__(self, issues: _Issues, content: ProjectContent) -> None:
        self._issues = issues
        self._content = content
        self._meta = content.problem.meta

    def check(self) -> None:
        if self._meta.track is not Track.PRACTICAL:
            self._error(f"project problems are on the {Track.PRACTICAL} track", "track")
        self._languages()
        self._project()
        self._comparator()
        self._types()
        self._approaches()
        self._forbidden_files()
        self._cases()

    def _error(self, message: str, location: str) -> None:
        self._issues.error(META_FILE, message, location)

    def _languages(self) -> None:
        languages = self._meta.languages
        if len(languages) != 1:
            self._error("a project problem lists exactly one language", "languages")
        elif languages[0] not in PROJECT_LANGUAGES:
            self._error(unsupported_language(languages[0]), "languages")

    def _project(self) -> None:
        project, language = self._meta.project, _language(self._content)
        if project is None:
            self._error("missing (kind: project)", "project")
            return
        if language is not None and (issue := entry_issue(project.entry, language)):
            self._error(issue, "project.entry")
        if issue := relative_path_issue(project.tests):
            self._error(f'"{project.tests}" {issue}', "project.tests")
        elif language is not None and (
            issue := level_tests_directory_issue(project.tests, language)
        ):
            self._error(issue, "project.tests")

    def _comparator(self) -> None:
        comparator = self._meta.comparator
        if comparator.type is not ComparatorType.OPS:
            self._error(
                f"project problems use the {ComparatorType.OPS} comparator", "comparator.type"
            )
        *others, last = GENERATED_TEST_COMPARATORS
        expressible = f"{', '.join(others)} or {last}"
        for name, compared in comparator.per_method.items():
            if compared not in GENERATED_TEST_COMPARATORS:
                message = f"generated tests compare with {expressible}, not {compared}"
                self._error(message, f"comparator.per_method.{name}")

    def _types(self) -> None:
        declared = {str(found): found for found in declared_types(self._meta.signature)}
        typescript = _language(self._content) is Language.TYPESCRIPT
        for text, found in declared.items():
            if _holds_node(found):
                message = "project problems take scalars, arrays and lists, not node types"
                self._error(f"{text}: {message}", "signature")
            elif typescript and Scalar.DECIMAL in scalars_of(found):
                message = (
                    "a TypeScript project cannot reach the Decimal class of the runner's "
                    "support module"
                )
                self._error(f"{text}: {message}", "signature")

    def _approaches(self) -> None:
        approaches = self._meta.approaches
        if len(approaches) != 1:
            message = f"a project problem has exactly one approach (has {len(approaches)})"
            self._error(message, "approaches")
        for index, approach in enumerate(approaches):
            if approach.oracle:
                self._error("a project problem has no oracle", f"approaches[{index}]")

    def _forbidden_files(self) -> None:
        for name in FORBIDDEN_FILES:
            if name in self._content.files:
                self._issues.error(name, "a project problem has none")
        if self._content.buggy_files:
            self._issues.error(BUGGY_DIRECTORY, "a project problem has none")

    def _cases(self) -> None:
        for index, case in enumerate(self._content.problem.cases):
            location = f"cases[{index}] {case.id}"
            if isinstance(case.input, GeneratedInput):
                self._issues.error(TESTS_FILE, "a project problem has no generate cases", location)
            elif isinstance(case.input, StressScenario):
                self._issues.error(TESTS_FILE, "a project problem has no stress cases", location)


def _holds_node(declared: ReturnType) -> bool:
    match declared:
        case NodeType():
            return True
        case ArrayType(element) | ListType(element):
            return _holds_node(element)
        case ScalarType() | VoidType():
            return False


class _Trees:
    """S15 on the starter and the overlays, and S16 on the generated test names."""

    def __init__(self, issues: _Issues, content: ProjectContent) -> None:
        self._issues = issues
        self._content = content
        files = content.problem.project_files or NO_PROJECT_FILES
        self._starter = files.starter
        self._overlays = files.overlays

    def check(self) -> None:
        for name, overlay in self._overlays.items():
            self._text_only(f"{SOLUTIONS_DIRECTORY}/{name}", overlay.files)
        starter = self._starter
        if starter is None:
            self._error("", "missing (kind: project)")
            return
        if README_FILE not in starter.paths:
            self._error(README_FILE, "missing")
        self._entry(starter)
        self._limits(starter)
        self._contents(starter)
        language = _language(self._content)
        if language is Language.PYTHON:
            _PythonStarter(self._error, starter).check()
        elif language is Language.TYPESCRIPT:
            _TypeScriptStarter(self._error, starter).check()
        elif language is Language.GO:
            entry = _well_formed_entry(self._content)
            slug = self._content.problem.meta.slug
            _GoStarter(self._error, starter, slug).check(entry[0].entry if entry else None)
        self._generated_test_names(starter)

    def _error(self, path: str, message: str) -> None:
        name = f"{STARTER_DIRECTORY}/{path}" if path else STARTER_DIRECTORY
        self._issues.error(name, message)

    def _entry(self, starter: ProjectTree) -> None:
        entry = _well_formed_entry(self._content)
        if entry is None:
            return
        project, language = entry
        candidates = entry_files(project.entry, language)
        if starter.paths.isdisjoint(candidates):
            self._error("", f"has no {' or '.join(candidates)} for the entry {project.entry}")

    def _limits(self, starter: ProjectTree) -> None:
        if len(starter.files) > MAX_STARTER_FILES:
            message = f"holds {len(starter.files)} files; at most {MAX_STARTER_FILES} are allowed"
            self._error("", message)
        if starter.size > MAX_STARTER_BYTES:
            message = f"holds {starter.size} bytes; at most {MAX_STARTER_KIB} KiB are allowed"
            self._error("", message)

    def _contents(self, starter: ProjectTree) -> None:
        """Caches and build output, lock files, and files that are not text."""
        caches = dict.fromkeys(_cache_path(file.path) for file in starter.files)
        for cache in caches:
            if cache is not None:
                self._error(cache, "is build output or a cache")
        plain = [file for file in starter.files if _cache_path(file.path) is None]
        for file in plain:
            if file.path.rpartition(PATH_SEPARATOR)[2] in LOCK_FILES:
                self._error(file.path, "is a lock file")
        self._text_only(STARTER_DIRECTORY, plain)

    def _text_only(self, folder: str, files: Iterable[ProjectFile]) -> None:
        for file in files:
            if file.text is None:
                self._issues.error(f"{folder}/{file.path}", "is not UTF-8 text")

    def _generated_test_names(self, starter: ProjectTree) -> None:
        """S16: `cstudy` writes its level tests under `project.tests` and never over a file."""
        project, language = self._content.problem.meta.project, _language(self._content)
        if project is None or language is None or relative_path_issue(project.tests):
            return
        pattern = level_test_pattern(language)
        under = f"{project.tests}{PATH_SEPARATOR}"
        for path in sorted(starter.paths):
            name = path.rpartition(PATH_SEPARATOR)[2]
            if path.startswith(under) and pattern.fullmatch(name):
                self._error(path, "has the name of a generated test file")


def _cache_path(path: str) -> str | None:
    """The cache directory `path` lies in, or `path` itself when it is build output."""
    segments = path.split(PATH_SEPARATOR)
    for index, segment in enumerate(segments[:-1]):
        if segment in CACHE_DIRECTORIES:
            return PATH_SEPARATOR.join(segments[: index + 1])
    return path if path.endswith(BUILD_OUTPUT_SUFFIXES) else None


class _PythonStarter:
    """S15: a `pyproject.toml` of tool settings only, and no top-level module that hides one the
    native tests import, since the project root comes first on `sys.path`."""

    def __init__(self, report: _Report, starter: ProjectTree) -> None:
        self._report = report
        self._starter = starter

    def check(self) -> None:
        self._pyproject()
        for module, path in _top_level_modules(self._starter).items():
            if module in sys.stdlib_module_names:
                self._report(path, f'is named after the standard-library module "{module}"')
            elif module in SHADOWED_PYTHON_MODULES:
                self._report(path, f'is named after the module "{module}"')

    def _pyproject(self) -> None:
        """A `[project]` table, `requires-python` or `[tool.uv]` can make `uv run` delete the
        shared venv through the project's `.venv` link."""
        file = self._starter.file(PYPROJECT_FILE)
        if file is None:
            self._report(PYPROJECT_FILE, "missing")
            return
        if file.text is None:
            return
        try:
            document = tomllib.loads(file.text)
        except tomllib.TOMLDecodeError as error:
            self._report(PYPROJECT_FILE, f"is not valid TOML: {error}")
            return
        if "project" in document:
            self._report(PYPROJECT_FILE, "has a [project] table")
        if "uv" in (_table(document.get("tool")) or {}):
            self._report(PYPROJECT_FILE, "has a [tool.uv] table")
        if _sets(document, REQUIRES_PYTHON):
            self._report(PYPROJECT_FILE, f"sets {REQUIRES_PYTHON}")


def _table(value: object) -> Mapping[str, object] | None:
    """`value` as a TOML table or a JSON object; None when it is something else."""
    return cast(dict[str, object], value) if isinstance(value, dict) else None


def _sets(table: Mapping[str, object], key: str) -> bool:
    """Whether `key` appears in `table` or in a table nested in it."""
    nested = (found for value in table.values() if (found := _table(value)) is not None)
    return key in table or any(_sets(found, key) for found in nested)


def _top_level_modules(starter: ProjectTree) -> dict[str, str]:
    """Each module or package at the top of the starter, with the path that defines it."""
    modules: dict[str, str] = {}
    for path in sorted(starter.paths):
        if not path.endswith(_PYTHON_SUFFIX):
            continue
        top, separator, _ = path.partition(PATH_SEPARATOR)
        modules.setdefault(top if separator else top.removesuffix(_PYTHON_SUFFIX), top)
    return modules


class _TypeScriptStarter:
    """S15: an ES module package that installs nothing, and a `tsconfig.json`."""

    def __init__(self, report: _Report, starter: ProjectTree) -> None:
        self._report = report
        self._starter = starter

    def check(self) -> None:
        self._package()
        if TSCONFIG_FILE not in self._starter.paths:
            self._report(TSCONFIG_FILE, "missing")

    def _package(self) -> None:
        file = self._starter.file(PACKAGE_FILE)
        if file is None:
            self._report(PACKAGE_FILE, "missing")
            return
        if file.text is None:
            return
        try:
            document: object = json.loads(file.text)
        except json.JSONDecodeError as error:
            self._report(PACKAGE_FILE, f"is not valid JSON: {error}")
            return
        package = _table(document)
        if package is None:
            self._report(PACKAGE_FILE, "is not a JSON object")
            return
        if package.get("type") != "module":
            self._report(PACKAGE_FILE, 'needs "type": "module"')
        for field in PACKAGE_DEPENDENCY_FIELDS:
            if package.get(field):
                self._report(PACKAGE_FILE, f"declares {field}")


class _GoStarter:
    """S15: a module named after the slug that builds offline, reaching only the vendored modules
    through the runtime's copies; the folder's `go.work` left to `cstudy start`; and an entry
    package that the grader can import."""

    def __init__(self, report: _Report, starter: ProjectTree, slug: str) -> None:
        self._report = report
        self._starter = starter
        self._slug = slug

    def check(self, entry: str | None) -> None:
        self._module()
        for name in (GO_WORK_FILE, GO_WORK_SUM_FILE):
            if name in self._starter.paths:
                self._report(name, f"cstudy start writes the folder's {GO_WORK_FILE}")
        entry_file = None if entry is None else self._starter.file(entry)
        if entry_file is not None and go_package_name(entry_file.text or "") == _GO_MAIN_PACKAGE:
            message = f"declares package {_GO_MAIN_PACKAGE}; the grader imports the entry's package"
            self._report(entry_file.path, message)

    def _module(self) -> None:
        file = self._starter.file(GO_MODULE_FILE)
        if file is None:
            self._report(GO_MODULE_FILE, "missing")
            return
        module = go_module_file(file.text or "")
        if module.module != self._slug:
            message = (
                f'declares module "{module.module}"; a project\'s module is its slug, {self._slug}'
            )
            self._report(GO_MODULE_FILE, message)
        if module.go != GO_WORK_VERSION:
            message = f'says "go {module.go}"; a project\'s go.mod says go {GO_WORK_VERSION}'
            self._report(GO_MODULE_FILE, message)
        for required, version in module.requires.items():
            if GO_VENDORED_MODULES.get(required) != version:
                message = (
                    f"requires {required} {version}, which is not vendored: a project builds "
                    f"offline, with {_vendored_go_modules()} only"
                )
                self._report(GO_MODULE_FILE, message)
            elif module.replaces.get(required) != (copy := go_vendored_replacement(required)):
                self._report(
                    GO_MODULE_FILE, f"does not replace {required} with {copy}, the runtime's copy"
                )


def _vendored_go_modules() -> str:
    return ", ".join(f"{module} {version}" for module, version in GO_VENDORED_MODULES.items())


class _Documents:
    """S16: `## Project` in problem.md after `## Output`, and `### Design` after `### Algorithm`
    in the approach's explanation."""

    def __init__(self, issues: _Issues, content: ProjectContent) -> None:
        self._issues = issues
        self._content = content

    def check(self) -> None:
        if self._content.problem_markdown is not None:
            self._project_section(MarkdownDocument(self._content.problem_markdown))
        if self._content.explanation is not None:
            self._design(Explanation(self._content.explanation))

    def _project_section(self, document: MarkdownDocument) -> None:
        project = document.section(PROJECT_SECTION)
        if project is None:
            self._issues.error(PROBLEM_FILE, f'missing "## {PROJECT_SECTION}"')
            return
        if not project.text:
            self._issues.error(PROBLEM_FILE, f'"## {PROJECT_SECTION}" is empty')
        if _comes_before(project, document.section(OUTPUT_SECTION)):
            message = f'"## {PROJECT_SECTION}" must come after "## {OUTPUT_SECTION}"'
            self._issues.error(PROBLEM_FILE, message)

    def _design(self, explanation: Explanation) -> None:
        declared = {approach.id for approach in self._content.problem.meta.approaches}
        for found in explanation.approaches():
            if found.approach_id not in declared:
                continue
            sections = explanation.document.sections(3, found.section)
            subsections = {section.title: section for section in sections}
            design = subsections.get(DESIGN_SUBSECTION)
            where = f"in approach {found.approach_id}"
            if design is None:
                self._error(f'missing "### {DESIGN_SUBSECTION}" {where}')
                continue
            if not design.text:
                self._error(f'"### {DESIGN_SUBSECTION}" is empty {where}')
            if _comes_before(design, subsections.get(ALGORITHM_SUBSECTION)):
                self._error(
                    f'"### {DESIGN_SUBSECTION}" must come after "### {ALGORITHM_SUBSECTION}" '
                    f"{where}"
                )

    def _error(self, message: str) -> None:
        self._issues.error(EXPLANATION_FILE, message)


def _comes_before(section: MarkdownSection, other: MarkdownSection | None) -> bool:
    return other is not None and section.start < other.start
