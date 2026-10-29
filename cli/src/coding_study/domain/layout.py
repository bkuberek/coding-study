"""Where user code, statements, archives and materialized references live.

Sources: docs/architecture.md#repository-layout, docs/specs/runners.md#stub-generation and
docs/specs/runners.md#reference-materialization. Paths are POSIX strings relative to the
workspace root (docs/specs/installation-and-workspaces.md#layout) unless a function takes `root`,
the absolute workspace root.
"""

from collections.abc import Mapping
from typing import assert_never

from coding_study.domain.items import ItemMeta
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import ClassTarget, FileTarget, RunTarget
from coding_study.domain.signature import ClassSignature

SOURCE_EXTENSIONS: Mapping[Language, str] = {
    Language.PYTHON: "py",
    Language.TYPESCRIPT: "ts",
    Language.JAVA: "java",
    Language.KOTLIN: "kt",
}
JVM_LANGUAGES = frozenset({Language.JAVA, Language.KOTLIN})
SOLUTION_CLASS = "Solution"
"""Function-kind problems on the JVM declare their method in this class."""
USER_PACKAGE = "practice"
REFERENCE_PACKAGE = "ref"
STATEMENTS_DIRECTORY = ".statements"
ARCHIVE_DIRECTORY = ".archive"
NOTES_DIRECTORY = "notes"
BUILD_DIRECTORY = ".cs/build"
PYTHON_PROJECT = "python"
PYTHON_VENV = ".venv"
PYTHON_INTERPRETER = f"{PYTHON_VENV}/bin/python"
"""The workspace interpreter, relative to `PYTHON_PROJECT`."""
TYPESCRIPT_PROJECT = "typescript"
JVM_PROJECT = "jvm"
"""The practice projects at the workspace root."""


def stub_path(meta: ProblemMeta, language: Language) -> str:
    """The user's file for `meta` in `language`."""
    match language:
        case Language.PYTHON:
            return f"{user_directory(language)}/{meta.snake_slug}.py"
        case Language.TYPESCRIPT:
            return f"{user_directory(language)}/{meta.slug}.ts"
        case Language.JAVA | Language.KOTLIN:
            return f"{_user_package_directory(meta, language)}/{_jvm_file_name(meta, language)}"
        case _:
            assert_never(language)


def user_directory(language: Language) -> str:
    """Where the user's files for `language` live: the files themselves, or on the JVM the
    problems' package directories."""
    match language:
        case Language.PYTHON:
            return f"{PYTHON_PROJECT}/{USER_PACKAGE}"
        case Language.TYPESCRIPT:
            return f"{TYPESCRIPT_PROJECT}/{USER_PACKAGE}"
        case Language.JAVA | Language.KOTLIN:
            return f"{_jvm_sources(JVM_PROJECT, language)}/{USER_PACKAGE}"
        case _:
            assert_never(language)


def watch_path(meta: ProblemMeta, language: Language) -> str:
    """What `cstudy test --watch` watches: the user file, or on the JVM the problem's package."""
    match language:
        case Language.PYTHON | Language.TYPESCRIPT:
            return stub_path(meta, language)
        case Language.JAVA | Language.KOTLIN:
            return _user_package_directory(meta, language)
        case _:
            assert_never(language)


def user_target(meta: ProblemMeta, language: Language, root: str) -> RunTarget:
    match language:
        case Language.PYTHON | Language.TYPESCRIPT:
            return FileTarget(f"{root}/{stub_path(meta, language)}")
        case Language.JAVA | Language.KOTLIN:
            return ClassTarget(f"{USER_PACKAGE}.{meta.snake_slug}.{jvm_class_name(meta)}")
        case _:
            assert_never(language)


def statement_path(slug: str) -> str:
    return f"{STATEMENTS_DIRECTORY}/{slug}.md"


def archive_directory(slug: str, attempt_id: int, language: Language) -> str:
    """Where `cstudy start --fresh` moves the previous attempt's file."""
    return f"{ARCHIVE_DIRECTORY}/{slug}/{attempt_id}-{language}"


def notes_path(meta: ItemMeta) -> str:
    """Where `cstudy start` puts the user's answer to a non-autograded item."""
    return f"{NOTES_DIRECTORY}/{meta.track}/{meta.slug}.md"


def notes_archive_directory(slug: str, attempt_id: int) -> str:
    """Where `cstudy start --fresh` and review attempts move the previous notes."""
    return f"{ARCHIVE_DIRECTORY}/{slug}/{attempt_id}-notes"


def jvm_class_name(meta: ProblemMeta) -> str:
    """The top-level JVM class: the declared class, or `Solution` for function kinds."""
    if isinstance(meta.signature, ClassSignature):
        return meta.signature.name
    return SOLUTION_CLASS


def reference_file_name(approach_id: str, language: Language) -> str:
    """A reference file inside the problem's `solutions/` directory."""
    return f"{approach_id}.{SOURCE_EXTENSIONS[language]}"


def language_of_extension(extension: str) -> Language | None:
    return next(
        (language for language, known in SOURCE_EXTENSIONS.items() if known == extension), None
    )


def reference_build_path(meta: ProblemMeta, approach_id: str, language: Language) -> str:
    """Where `cstudy verify` and `cstudy bench` materialize a reference before running it."""
    approach = snake_case(approach_id)
    match language:
        case Language.PYTHON:
            return f"{BUILD_DIRECTORY}/python/{REFERENCE_PACKAGE}/{meta.snake_slug}/{approach}.py"
        case Language.TYPESCRIPT:
            return f"{BUILD_DIRECTORY}/typescript/{REFERENCE_PACKAGE}/{meta.slug}/{approach_id}.ts"
        case Language.JAVA | Language.KOTLIN:
            sources = _jvm_sources(f"{BUILD_DIRECTORY}/jvm", language)
            package_directory = jvm_reference_package(meta, approach_id).replace(".", "/")
            return f"{sources}/{package_directory}/{_jvm_file_name(meta, language)}"
        case _:
            assert_never(language)


def reference_target(
    meta: ProblemMeta, approach_id: str, language: Language, root: str
) -> RunTarget:
    match language:
        case Language.PYTHON | Language.TYPESCRIPT:
            return FileTarget(f"{root}/{reference_build_path(meta, approach_id, language)}")
        case Language.JAVA | Language.KOTLIN:
            return ClassTarget(f"{jvm_reference_package(meta, approach_id)}.{jvm_class_name(meta)}")
        case _:
            assert_never(language)


def jvm_reference_package(meta: ProblemMeta, approach_id: str) -> str:
    """The package the materializer prepends to a JVM reference file."""
    return f"{REFERENCE_PACKAGE}.{meta.snake_slug}.{snake_case(approach_id)}"


def _user_package_directory(meta: ProblemMeta, language: Language) -> str:
    return f"{user_directory(language)}/{meta.snake_slug}"


def _jvm_sources(project: str, language: Language) -> str:
    return f"{project}/{language}/src/main/{language}"


def _jvm_file_name(meta: ProblemMeta, language: Language) -> str:
    return f"{jvm_class_name(meta)}.{SOURCE_EXTENSIONS[language]}"


def snake_case(identifier: str) -> str:
    """`two-sum` as `two_sum`: how file and package names spell a slug or an approach id."""
    return identifier.replace("-", "_")
