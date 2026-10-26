"""`stub: buggy` (docs/specs/problem-format.md#metayaml): the code a debugging problem hands out.

Buggy files (`buggy/solution.<ext>`, one per language) follow the reference file conventions:
no `package` line on the JVM. `cstudy start` adds the user's `practice.<snake_slug>` package;
`cstudy verify` runs the file like a reference under a reserved approach id and requires it to
fail.
"""

from coding_study.domain.layout import JVM_LANGUAGES, SOURCE_EXTENSIONS, USER_PACKAGE
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.problem_files import BUGGY_DIRECTORY

BUGGY_STUB_APPROACH_ID = "buggy-stub"
BUGGY_FILE_STEM = "solution"


def buggy_file_name(language: Language) -> str:
    """The file name inside `buggy/`."""
    return f"{BUGGY_FILE_STEM}.{SOURCE_EXTENSIONS[language]}"


def buggy_file(language: Language) -> str:
    """Relative to the problem directory."""
    return f"{BUGGY_DIRECTORY}/{buggy_file_name(language)}"


def buggy_as_stub(meta: ProblemMeta, language: Language, buggy: str) -> str:
    """The user's file: the buggy code, in the `practice.<snake_slug>` package on the JVM."""
    if language not in JVM_LANGUAGES:
        return buggy
    terminator = ";" if language is Language.JAVA else ""
    return f"package {USER_PACKAGE}.{meta.snake_slug}{terminator}\n\n{buggy}"
