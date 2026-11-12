"""The generated starter with the problem's helper for its language, read from `helpers/`
(docs/specs/problem-format.md#starter-helpers): what `cstudy start` writes and D1 builds."""

from coding_study.application.ports import ProblemFiles
from coding_study.domain.problem import Language
from coding_study.domain.problem_files import HELPERS_DIRECTORY
from coding_study.domain.stub_helpers import helper_file, with_helper


def append_helper(files: ProblemFiles, slug: str, language: Language, stub: str) -> str:
    """`stub`, followed by the problem's helper for `language` when it has one."""
    name = helper_file(language, files.file_names(slug, HELPERS_DIRECTORY))
    helper = None if name is None else files.read_text(slug, name)
    return with_helper(stub, helper, language)
