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
from coding_study.domain.naming import RESERVED_WORDS, NameRole, is_reserved, member_name
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
    ValueType,
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
_GO_SOURCE_SUFFIX = ".go"
_GO_TEST_SUFFIX = "_test.go"
_GO_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_GO_PACKAGE_CLAUSE = re.compile(r"^package\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
_PACKAGE_SEPARATOR = "."
_JVM_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
RUST_LIBRARY_ROOT = "src/lib.rs"
"""Where a Rust project's library crate starts, and where its entry class is public."""
RUST_TESTS_DIRECTORY = "tests"
"""Where Cargo finds integration tests, so where a Rust project's level tests go."""
_RUST_CRATE_NAME = re.compile(r"[a-z][a-z0-9_]*")
RUST_NAMED_CRATES = frozenset(
    {
        *("std", "core", "alloc", "proc_macro", "test"),
        *("user", "cs_runner", "cs_support"),
        *("rust_decimal", "chrono", "arrayvec", "num_traits", "autocfg"),
    }
)
"""Crates the harness or a test already names: the standard library's, the bridge's alias of the
project crate (`user`), the runner's and the vendored ones."""
RUST_VENDORED_CRATES: Mapping[str, str] = {
    "chrono": '{ version = "=0.4.45", default-features = false, features = ["std"] }',
    "rust_decimal": '{ version = "=1.43.0", default-features = false, features = ["maths"] }',
}
"""The crates of `decimal` and `date`, vendored with the runner, and the only ones a Rust project
may depend on: declared exactly as the runner declares them, so a project, the harness and the
runner share one copy of each."""
RUST_SCALAR_CRATES: Mapping[Scalar, str] = {
    Scalar.DECIMAL: "rust_decimal",
    Scalar.DATE: "chrono",
}
"""The vendored crate whose type a scalar is in Rust."""


@dataclass(frozen=True, slots=True)
class Project:
    """The `project` block of meta.yaml."""

    entry: str
    """Where the entry class lives: a dotted module in Python (`bank.bank`), a file relative to the
    project root in TypeScript (`src/bank.ts`), the class's fully qualified name in Java and
    Kotlin (`bank.Bank`)."""
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


def level_tests_directory_issue(tests: str, language: Language) -> str | None:
    """Why `tests` cannot hold the generated test files of a project in `language`, beyond
    `relative_path_issue`; None when it can. Go's files declare `package <last name>_test`; Java
    and Kotlin need a package directory of the test sources.

    Raises ValueError for a language without project problems.
    """
    return _project_language(language).level_tests_directory_issue(tests)


def project_tests_package(project: Project, language: Language) -> str:
    """The package of a Java or Kotlin project's generated tests, from their directory:
    `src/test/java/com/bank` holds `com.bank`.

    Raises ValueError for a language whose tests have no package, or whose project problems are
    not supported.
    """
    root = _project_language(language).test_sources
    if root is None:
        raise ValueError(f"{language} tests have no package")
    return project.tests.removeprefix(f"{root}{PATH_SEPARATOR}").replace(
        PATH_SEPARATOR, _PACKAGE_SEPARATOR
    )


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


def go_package_name(source: str) -> str | None:
    """The name in the first `package` clause of a Go file; None when it has none."""
    match = _GO_PACKAGE_CLAUSE.search(source)
    return match.group(1) if match else None


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
    bool` in Python, `createAccount(timestamp: number, accountId: string): boolean` in TypeScript,
    `boolean createAccount(long timestamp, String accountId)` in Java.

    Raises ValueError for a language without project problems.
    """
    declare = _project_language(language).declare
    params = tuple(
        (member_name(param.name, language, NameRole.PARAMETER), param.type)
        for param in method.params
    )
    return declare(member_name(method.name, language, NameRole.METHOD), params, method.returns.type)


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


type _Declare = Callable[[str, tuple[tuple[str, ValueType], ...], ReturnType], str]
"""A method as the statement's `Methods to add:` line spells it, from its name, its parameters'
names and types and its return type, with the types as the language's stubs spell them."""


@dataclass(frozen=True, slots=True)
class _ProjectLanguage:
    entry_issue: Callable[[str], str | None]
    entry_files: Callable[[str], tuple[str, ...]]
    level_test_prefix: str
    level_test_suffix: str
    """A generated test file is named prefix, level number, suffix."""
    declare: _Declare
    level_tests_directory_issue: Callable[[str], str | None] = lambda _tests: None
    """Why a `project.tests` directory cannot hold the generated files, beyond its path."""
    test_sources: str | None = None
    """Java and Kotlin: the directory of the test sources, where the generated tests go to a
    package directory; None where they may go to any directory."""


@dataclass(frozen=True, slots=True)
class _Annotated:
    """`name(param: type, ...)` and the return type after `returns_separator`: the declarations
    of Python, TypeScript, Go and Kotlin."""

    type_text: Callable[[ReturnType], str]
    returns_separator: str
    """Between a method's parameters and its return type; a method whose type spells as nothing
    (Go's and Kotlin's `void`) has neither."""
    parameter_separator: str = ": "
    """Between a parameter's name and its type."""

    def __call__(
        self, name: str, params: tuple[tuple[str, ValueType], ...], returns: ReturnType
    ) -> str:
        listed = ", ".join(
            f"{param}{self.parameter_separator}{self.type_text(declared)}"
            for param, declared in params
        )
        declared = f"{name}({listed})"
        returned = self.type_text(returns)
        return f"{declared}{self.returns_separator}{returned}" if returned else declared


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


def _go_entry_issue(entry: str) -> str | None:
    is_source = entry.endswith(_GO_SOURCE_SUFFIX) and not entry.endswith(_GO_TEST_SUFFIX)
    if is_source and relative_path_issue(entry) is None:
        return None
    return f'"{entry}" is not a .go file inside the project such as bank.go, other than a test file'


def _go_level_tests_directory_issue(tests: str) -> str | None:
    """The generated files declare `package <last directory name>_test`."""
    name = tests.rpartition(PATH_SEPARATOR)[2]
    if _GO_IDENTIFIER.fullmatch(name) and name not in RESERVED_WORDS[Language.GO]:
        return None
    return f'"{tests}" does not end in a Go package name such as tests'


def _rust_entry_issue(entry: str) -> str | None:
    if not _RUST_CRATE_NAME.fullmatch(entry):
        return f'"{entry}" is not a crate name such as bank: lowercase letters, digits and _'
    if entry in RESERVED_WORDS[Language.RUST]:
        return f'"{entry}" is a Rust keyword'
    if entry in RUST_NAMED_CRATES:
        return f'"{entry}" is a crate the build or the tests already name'
    return None


def _rust_level_tests_directory_issue(tests: str) -> str | None:
    """Cargo finds integration tests in `tests/` only."""
    if tests == RUST_TESTS_DIRECTORY:
        return None
    return f'"{tests}" is not {RUST_TESTS_DIRECTORY}, where Cargo finds integration tests'


def _rust_declaration(
    name: str, params: tuple[tuple[str, ValueType], ...], returns: ReturnType
) -> str:
    """As the single-file stubs declare a method: `&mut self` first, no `->` for `void`."""
    listed = ", ".join(
        ("&mut self", *(f"{param}: {_rust_type(declared)}" for param, declared in params))
    )
    returned = _rust_type(returns)
    return f"{name}({listed}) -> {returned}" if returned else f"{name}({listed})"


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
_RUST_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "i32",
    Scalar.LONG: "i64",
    Scalar.DOUBLE: "f64",
    Scalar.BOOL: "bool",
    Scalar.STRING: "String",
    Scalar.CHAR: "char",
    Scalar.DECIMAL: "Decimal",
    Scalar.DATE: "NaiveDate",
}


_GO_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "int64",
    Scalar.DOUBLE: "float64",
    Scalar.BOOL: "bool",
    Scalar.STRING: "string",
    Scalar.CHAR: "rune",
    Scalar.DECIMAL: "decimal.Decimal",
    Scalar.DATE: "time.Time",
}
"""The Go mapping (docs/specs/problem-format.md#go-and-rust-mapping)."""


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


def _rust_type(declared: ReturnType) -> str:
    """As the Rust stubs spell it; empty for `void`, which a Rust method leaves out."""
    match declared:
        case ScalarType(scalar):
            return _RUST_SCALARS[scalar]
        case NodeType(kind):
            return f"Option<Box<{kind}>>"
        case ArrayType(element) | ListType(element):
            return f"Vec<{_rust_type(element)}>"
        case VoidType():
            return ""


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


def _go_type(declared: ReturnType) -> str:
    """A `void` result spells as nothing: a Go method without one declares no type."""
    match declared:
        case ScalarType(scalar):
            return _GO_SCALARS[scalar]
        case NodeType(kind):
            return f"*{kind}"
        case ArrayType(element) | ListType(element):
            return f"[]{_go_type(element)}"
        case VoidType():
            return ""


def _jvm_entry_issue(entry: str) -> str | None:
    """A class in a named package, every part an identifier of both Java and Kotlin."""
    parts = entry.split(_PACKAGE_SEPARATOR)
    if len(parts) < 2 or not all(_JVM_IDENTIFIER.fullmatch(part) for part in parts):
        return (
            f'"{entry}" is not the fully qualified name of a class in a package, such as bank.Bank'
        )
    keyword = next((part for part in parts if _is_jvm_keyword(part)), None)
    return None if keyword is None else f'"{entry}" holds the keyword "{keyword}"'


def _package_directory_issue(tests: str, test_sources: str) -> str | None:
    root = f"{test_sources}{PATH_SEPARATOR}"
    parts = tests.removeprefix(root).split(PATH_SEPARATOR)
    is_package = all(
        _JVM_IDENTIFIER.fullmatch(part) and not _is_jvm_keyword(part) for part in parts
    )
    if tests.startswith(root) and is_package:
        return None
    return f'"{tests}" is not a package directory under {root}, such as {root}bank'


def _is_jvm_keyword(word: str) -> bool:
    return is_reserved(word, Language.JAVA) or is_reserved(word, Language.KOTLIN)


@dataclass(frozen=True, slots=True)
class _ClassFile:
    """The source file of a fully qualified class: `bank.Bank` in `src/main/java/bank/Bank.java`."""

    main_sources: str
    suffix: str

    def __call__(self, entry: str) -> tuple[str, ...]:
        path = entry.replace(_PACKAGE_SEPARATOR, PATH_SEPARATOR)
        return (f"{self.main_sources}{PATH_SEPARATOR}{path}{self.suffix}",)


_JAVA_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "long",
    Scalar.DOUBLE: "double",
    Scalar.BOOL: "boolean",
    Scalar.STRING: "String",
    Scalar.CHAR: "char",
    Scalar.DECIMAL: "BigDecimal",
    Scalar.DATE: "LocalDate",
}
_JAVA_BOXED: Mapping[Scalar, str] = {
    **_JAVA_SCALARS,
    Scalar.INT: "Integer",
    Scalar.LONG: "Long",
    Scalar.DOUBLE: "Double",
    Scalar.BOOL: "Boolean",
    Scalar.CHAR: "Character",
}
"""A list holds objects: the wrapper class of each primitive."""
_KOTLIN_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "Int",
    Scalar.LONG: "Long",
    Scalar.DOUBLE: "Double",
    Scalar.BOOL: "Boolean",
    Scalar.STRING: "String",
    Scalar.CHAR: "Char",
    Scalar.DECIMAL: "BigDecimal",
    Scalar.DATE: "LocalDate",
}
_KOTLIN_PRIMITIVE_ARRAYS: Mapping[Scalar, str] = {
    Scalar.INT: "IntArray",
    Scalar.LONG: "LongArray",
    Scalar.DOUBLE: "DoubleArray",
    Scalar.BOOL: "BooleanArray",
    Scalar.CHAR: "CharArray",
}


def _java_type(declared: ReturnType) -> str:
    match declared:
        case ScalarType(scalar):
            return _JAVA_SCALARS[scalar]
        case NodeType(kind):
            return f"{kind}"
        case ArrayType(element):
            return f"{_java_type(element)}[]"
        case ListType(ScalarType(scalar)):
            return f"List<{_JAVA_BOXED[scalar]}>"
        case ListType(element):
            return f"List<{_java_type(element)}>"
        case VoidType():
            return "void"


def _kotlin_type(declared: ReturnType) -> str:
    """A `void` result spells as nothing: a Kotlin function without one leaves out `Unit`."""
    match declared:
        case ScalarType(scalar):
            return _KOTLIN_SCALARS[scalar]
        case NodeType(kind):
            return f"{kind}?"
        case ArrayType(ScalarType(scalar)) if scalar in _KOTLIN_PRIMITIVE_ARRAYS:
            return _KOTLIN_PRIMITIVE_ARRAYS[scalar]
        case ArrayType(element):
            return f"Array<{_kotlin_type(element)}>"
        case ListType(element):
            return f"List<{_kotlin_type(element)}>"
        case VoidType():
            return ""


def _java_declaration(
    name: str, params: tuple[tuple[str, ValueType], ...], returns: ReturnType
) -> str:
    listed = ", ".join(f"{_java_type(declared)} {param}" for param, declared in params)
    return f"{_java_type(returns)} {name}({listed})"


def _jvm_language(sources: str, suffix: str, declare: _Declare) -> _ProjectLanguage:
    """Java's or Kotlin's rules, the sources of the language under `src/main/<sources>` and
    `src/test/<sources>`."""
    test_sources = f"src/test/{sources}"
    return _ProjectLanguage(
        _jvm_entry_issue,
        _ClassFile(f"src/main/{sources}", suffix),
        "Level",
        f"Test{suffix}",
        declare,
        lambda tests: _package_directory_issue(tests, test_sources),
        test_sources,
    )


_PROJECT_LANGUAGES: Mapping[Language, _ProjectLanguage | None] = {
    Language.PYTHON: _ProjectLanguage(
        _python_entry_issue,
        _python_entry_files,
        "test_level_",
        ".py",
        _Annotated(_python_type, " -> "),
    ),
    Language.TYPESCRIPT: _ProjectLanguage(
        _typescript_entry_issue,
        lambda entry: (entry,),
        "level-",
        ".test.ts",
        _Annotated(_typescript_type, ": "),
    ),
    Language.JAVA: _jvm_language("java", ".java", _java_declaration),
    Language.KOTLIN: _jvm_language("kotlin", ".kt", _Annotated(_kotlin_type, ": ")),
    Language.GO: _ProjectLanguage(
        _go_entry_issue,
        lambda entry: (entry,),
        "level_",
        _GO_TEST_SUFFIX,
        _Annotated(_go_type, " ", parameter_separator=" "),
        _go_level_tests_directory_issue,
    ),
    Language.RUST: _ProjectLanguage(
        _rust_entry_issue,
        lambda _entry: (RUST_LIBRARY_ROOT,),
        "level_",
        ".rs",
        _rust_declaration,
        _rust_level_tests_directory_issue,
    ),
}
"""None: a language whose project problems are not yet supported."""
PROJECT_LANGUAGES = tuple(language for language, found in _PROJECT_LANGUAGES.items() if found)
"""The languages a project problem may list."""


def unsupported_language(language: Language) -> str:
    return f"project problems are not yet supported in {language}"


def _project_language(language: Language) -> _ProjectLanguage:
    found = _PROJECT_LANGUAGES[language]
    if found is None:
        raise ValueError(unsupported_language(language))
    return found
