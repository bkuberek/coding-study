"""The grading job of a project problem (docs/specs/runners.md#grading-job).

A grading job is a class job whose target is the project folder. The runner checks, when the job
loads, that every method the request declares exists, so the request declares only the methods
of the levels it grades: a method of a locked level never has to exist.
"""

from dataclasses import replace

from coding_study.domain.layout import COMPILED_USER_TARGET
from coding_study.domain.problem import Language
from coding_study.domain.project import Project, unsupported_language
from coding_study.domain.runs import (
    ClassTarget,
    CompiledTarget,
    FileTarget,
    ProjectTarget,
    RunTarget,
)
from coding_study.domain.signature import ClassSignature, Signature


def grading_target(project: Project, language: Language, root: str) -> RunTarget:
    """What the runner loads from the project folder at `root` (absolute): a Python project is
    the folder and its entry module, a TypeScript one its entry file, a Java or Kotlin one its
    entry class, on the classpath of the folder's build, and a Go one the user's package, which
    the runner binary was compiled with.

    Raises ValueError for a language without project problems.
    """
    match language:
        case Language.PYTHON:
            return ProjectTarget(root, project.entry)
        case Language.TYPESCRIPT:
            return FileTarget(f"{root}/{project.entry}")
        case Language.JAVA | Language.KOTLIN:
            return ClassTarget(project.entry)
        case Language.GO:
            return CompiledTarget(COMPILED_USER_TARGET)
        case _:
            raise ValueError(unsupported_language(language))


def graded_signature(signature: Signature, level: int) -> ClassSignature:
    """The entry class with the methods of levels 1 to `level`, and any method without a level.

    Raises ValueError for a function signature, which has no levels.
    """
    if not isinstance(signature, ClassSignature):
        raise ValueError(f"a graded signature is a class signature, not {signature.name}()")
    methods = tuple(
        method for method in signature.methods if method.level is None or method.level <= level
    )
    return replace(signature, methods=methods)
