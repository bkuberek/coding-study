"""Project problems (docs/specs/problem-format.md#project-problems): a folder of seeded files in
one language, graded through an entry class and opened in levels as progressive problems are.

The `project` block of meta.yaml names the entry and the directory that receives the native test
files `cstudy` generates per level. `starter/` and each approach's `solutions/<approach>/`, an
overlay of changed and added files on the starter, are trees of plain files. Paths inside a project
folder are relative and `/`-separated, and none may lead out of the folder.

A project problem is solved in its one language, and its statement speaks it: examples name the
methods as that language does, and each level opens with the methods it adds, declared in that
language (docs/specs/problem-format.md#statement).
"""

import keyword
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace

from coding_study.domain.cases import OperationSequence
from coding_study.domain.levels import level_heading
from coding_study.domain.markdown import MarkdownDocument
from coding_study.domain.naming import NameRole, member_name
from coding_study.domain.problem import Language, Problem, ProblemMeta
from coding_study.domain.signature import ClassSignature, Method, Param, Signature
from coding_study.domain.statement import render_statement
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    VoidType,
)

DEFAULT_TESTS_DIRECTORY = "tests"
METHODS_TO_ADD = "Methods to add:"
"""Opens each level of a project problem's statement, before the methods the level adds."""
PATH_SEPARATOR = "/"
_PARENT_SEGMENT = ".."
_CURRENT_SEGMENT = "."
_WINDOWS_SEPARATOR = "\\"
_PYTHON_SOURCE_SUFFIX = ".py"
_PYTHON_PACKAGE_FILE = "__init__.py"
_TYPESCRIPT_SOURCE_SUFFIX = ".ts"


@dataclass(frozen=True, slots=True)
class Project:
    """The `project` block of meta.yaml."""

    entry: str
    """Where the entry class lives: a dotted module in Python (`bank.bank`), a file relative to the
    project root in TypeScript (`src/bank.ts`)."""
    tests: str = DEFAULT_TESTS_DIRECTORY
    """The directory, relative to the project root, that receives the generated level tests."""


@dataclass(frozen=True, slots=True)
class ProjectFile:
    path: str
    """Relative to its folder, as `relative_path_issue` requires."""
    size: int
    """In bytes."""
    text: str | None
    """The content, when it is UTF-8 without NUL bytes; None otherwise."""

    def __post_init__(self) -> None:
        issue = relative_path_issue(self.path)
        if issue is not None:
            raise ValueError(f'project file "{self.path}" {issue}')


@dataclass(frozen=True, slots=True)
class ProjectTree:
    """The plain files of one folder, in path order."""

    files: tuple[ProjectFile, ...]

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(file.path for file in self.files)

    @property
    def size(self) -> int:
        return sum(file.size for file in self.files)

    def file(self, path: str) -> ProjectFile | None:
        return next((file for file in self.files if file.path == path), None)


@dataclass(frozen=True, slots=True)
class ProjectFiles:
    """The trees in a project problem's directory."""

    starter: ProjectTree | None
    """`starter/`, or None when the problem has none."""
    overlays: Mapping[str, ProjectTree] = field(default_factory=dict[str, ProjectTree])
    """Every directory in `solutions/` by name: the reference of the approach it names, as the
    files it changes or adds on the starter."""


NO_PROJECT_FILES = ProjectFiles(None)
"""What a problem without trees has: no starter and no overlays."""


def relative_path_issue(path: str) -> str | None:
    """Why `path` cannot name a file or directory inside a folder; None when it can.

    A valid path is relative, `/`-separated and canonical: no `..` that could leave the folder,
    and no empty or `.` segment, so that equal paths are equal strings.
    """
    if not path:
        return "is empty"
    if path.startswith(PATH_SEPARATOR):
        return "is absolute"
    if _WINDOWS_SEPARATOR in path:
        return f"uses {_WINDOWS_SEPARATOR} instead of {PATH_SEPARATOR}"
    segments = path.split(PATH_SEPARATOR)
    if _PARENT_SEGMENT in segments:
        return f'leaves its folder through "{_PARENT_SEGMENT}"'
    if any(segment in ("", _CURRENT_SEGMENT) for segment in segments):
        return f'has an empty or "{_CURRENT_SEGMENT}" segment'
    return None


def entry_issue(entry: str, language: Language) -> str | None:
    """Why `entry` cannot name the entry of a project in `language`; None when it can.

    Raises ValueError for a language without project problems.
    """
    return _project_language(language).entry_issue(entry)


def entry_files(entry: str, language: Language) -> tuple[str, ...]:
    """The project files, any one of which defines a well-formed `entry`.

    Raises ValueError for a language without project problems.
    """
    return _project_language(language).entry_files(entry)


def level_test_file(project: Project, language: Language, level: int) -> str:
    """The generated test file of `level`, relative to the project root.

    Raises ValueError for a language without project problems.
    """
    names = _project_language(language)
    name = f"{names.level_test_prefix}{level}{names.level_test_suffix}"
    return f"{project.tests}{PATH_SEPARATOR}{name}"


def level_test_pattern(language: Language) -> re.Pattern[str]:
    """Matches the file name of a generated test file of any level.

    Raises ValueError for a language without project problems.
    """
    names = _project_language(language)
    prefix, suffix = re.escape(names.level_test_prefix), re.escape(names.level_test_suffix)
    return re.compile(f"{prefix}[1-9][0-9]*{suffix}")


def project_language(meta: ProblemMeta) -> Language:
    """The one language a project problem is solved in.

    Raises ValueError when `meta` lists another number of languages, or a language without
    project problems.
    """
    if len(meta.languages) != 1:
        raise ValueError(f"{meta.slug} lists {len(meta.languages)} languages, not one")
    language = meta.languages[0]
    _project_language(language)
    return language


def method_text(method: Method, language: Language) -> str:
    """`method` as `language` declares it: `create_account(timestamp: int, account_id: str) ->
    bool` in Python, `createAccount(timestamp: number, accountId: string): boolean` in TypeScript.

    Raises ValueError for a language without project problems.
    """
    names = _project_language(language)
    params = ", ".join(
        f"{member_name(param.name, language, NameRole.PARAMETER)}: {names.type_text(param.type)}"
        for param in method.params
    )
    name = member_name(method.name, language, NameRole.METHOD)
    return f"{name}({params}){names.returns_separator}{names.type_text(method.returns.type)}"


def level_methods(signature: ClassSignature, level: int) -> tuple[Method, ...]:
    """The methods `level` adds, in declaration order."""
    return tuple(method for method in signature.methods if method.level == level)


def in_language_names(problem: Problem) -> Problem:
    """`problem` with its methods, their parameters, its operations and its per-method
    comparators named as its language names them. The class keeps its name.

    Raises ValueError for a problem without one language that has project problems.
    """
    language = project_language(problem.meta)
    meta = problem.meta
    comparator = replace(
        meta.comparator,
        per_method={
            _method_name(name, language): compared
            for name, compared in meta.comparator.per_method.items()
        },
    )
    signature = _named_signature(meta.signature, language)
    named = replace(meta, signature=signature, comparator=comparator)
    cases = tuple(
        replace(case, input=in_language_operations(case.input, language))
        if isinstance(case.input, OperationSequence)
        else case
        for case in problem.cases
    )
    return replace(problem, meta=named, cases=cases)


def render_project_statement(
    problem: Problem, problem_markdown: str | None, unlocked_level: int | None
) -> str:
    """`render_statement` in the problem's language: examples name its methods as the language
    does, and each level of problem.md opens with a `Methods to add:` line, unless it adds none.
    """
    language = project_language(problem.meta)
    markdown = problem_markdown
    if markdown is not None and isinstance(problem.meta.signature, ClassSignature):
        markdown = _with_methods_to_add(markdown, problem.meta.signature, language)
    return render_statement(in_language_names(problem), markdown, unlocked_level)


def _with_methods_to_add(markdown: str, signature: ClassSignature, language: Language) -> str:
    document = MarkdownDocument(markdown)
    lines = list(document.lines)
    for section in reversed(document.sections(2)):
        number = level_heading(section.title)
        methods = level_methods(signature, number) if number is not None else ()
        if not methods:
            continue
        added = ", ".join(method_text(method, language) for method in methods)
        after = section.start + 1
        separated = after < len(lines) and not lines[after].strip()
        lines[after:after] = ["", f"{METHODS_TO_ADD} {added}", *([] if separated else [""])]
    return "\n".join(lines) + "\n"


def _named_signature(signature: Signature, language: Language) -> Signature:
    if not isinstance(signature, ClassSignature):
        return signature
    methods = tuple(
        replace(
            method,
            name=_method_name(method.name, language),
            params=_named_params(method.params, language),
        )
        for method in signature.methods
    )
    constructor = _named_params(signature.constructor_params, language)
    return replace(signature, constructor_params=constructor, methods=methods)


def _named_params(params: tuple[Param, ...], language: Language) -> tuple[Param, ...]:
    return tuple(
        replace(param, name=member_name(param.name, language, NameRole.PARAMETER))
        for param in params
    )


def in_language_operations(sequence: OperationSequence, language: Language) -> OperationSequence:
    """`sequence` with its methods named as `language` names them; the constructor keeps the
    class's name."""
    constructor, *operations = sequence.ops
    named = (constructor, *(_method_name(operation, language) for operation in operations))
    return replace(sequence, ops=named)


def _method_name(canonical: str, language: Language) -> str:
    return member_name(canonical, language, NameRole.METHOD)


@dataclass(frozen=True, slots=True)
class _ProjectLanguage:
    entry_issue: Callable[[str], str | None]
    entry_files: Callable[[str], tuple[str, ...]]
    level_test_prefix: str
    level_test_suffix: str
    """A generated test file is named prefix, level number, suffix."""
    type_text: Callable[[ReturnType], str]
    """A type as the statement's `Methods to add:` line spells it, as the language's stubs do."""
    returns_separator: str
    """Between a method's parameters and its return type."""


def _python_entry_issue(entry: str) -> str | None:
    modules = entry.split(".")
    if all(module.isidentifier() and not keyword.iskeyword(module) for module in modules):
        return None
    return f'"{entry}" is not a dotted module name such as bank.bank'


def _python_entry_files(entry: str) -> tuple[str, ...]:
    """A module file, or the `__init__.py` of a package."""
    module = entry.replace(".", PATH_SEPARATOR)
    return (
        f"{module}{_PYTHON_SOURCE_SUFFIX}",
        f"{module}{PATH_SEPARATOR}{_PYTHON_PACKAGE_FILE}",
    )


def _typescript_entry_issue(entry: str) -> str | None:
    if entry.endswith(_TYPESCRIPT_SOURCE_SUFFIX) and relative_path_issue(entry) is None:
        return None
    return f'"{entry}" is not a .ts file inside the project such as src/bank.ts'


_PYTHON_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "int",
    Scalar.DOUBLE: "float",
    Scalar.BOOL: "bool",
    Scalar.STRING: "str",
    Scalar.CHAR: "str",
    Scalar.DECIMAL: "Decimal",
    Scalar.DATE: "date",
}
_TYPESCRIPT_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "number",
    Scalar.LONG: "number",
    Scalar.DOUBLE: "number",
    Scalar.BOOL: "boolean",
    Scalar.STRING: "string",
    Scalar.CHAR: "string",
    Scalar.DECIMAL: "Decimal",
    Scalar.DATE: "string",
}
"""A project folder cannot reach the runner's support module, so a date is its ISO string."""


def _python_type(declared: ReturnType) -> str:
    match declared:
        case ScalarType(scalar):
            return _PYTHON_SCALARS[scalar]
        case NodeType(kind):
            return f"{kind} | None"
        case ArrayType(element) | ListType(element):
            return f"list[{_python_type(element)}]"
        case VoidType():
            return "None"


def _typescript_type(declared: ReturnType) -> str:
    match declared:
        case ScalarType(scalar):
            return _TYPESCRIPT_SCALARS[scalar]
        case NodeType(kind):
            return f"{kind} | null"
        case ArrayType(element) | ListType(element):
            text = _typescript_type(element)
            return f"({text})[]" if isinstance(element, NodeType) else f"{text}[]"
        case VoidType():
            return "void"


_PROJECT_LANGUAGES: Mapping[Language, _ProjectLanguage | None] = {
    Language.PYTHON: _ProjectLanguage(
        _python_entry_issue, _python_entry_files, "test_level_", ".py", _python_type, " -> "
    ),
    Language.TYPESCRIPT: _ProjectLanguage(
        _typescript_entry_issue,
        lambda entry: (entry,),
        "level-",
        ".test.ts",
        _typescript_type,
        ": ",
    ),
    Language.JAVA: None,
    Language.KOTLIN: None,
    Language.GO: None,
    Language.RUST: None,
}
"""None: not yet supported; Java, Kotlin, Go and Rust wait for spikes (ADR 0014)."""
PROJECT_LANGUAGES = tuple(language for language, found in _PROJECT_LANGUAGES.items() if found)
"""The languages a project problem may list."""


def unsupported_language(language: Language) -> str:
    return f"project problems are not yet supported in {language}"


def _project_language(language: Language) -> _ProjectLanguage:
    found = _PROJECT_LANGUAGES[language]
    if found is None:
        raise ValueError(unsupported_language(language))
    return found
