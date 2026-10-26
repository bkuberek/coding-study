from coding_study.application.environment import Environment
from coding_study.domain.comparators import Comparator, comparator_for
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem import ComparatorType, ProblemMeta
from coding_study.domain.problem_files import CHECKER_FILE


def problem_comparator(environment: Environment, meta: ProblemMeta) -> Comparator:
    """The problem's comparator; `checker` problems load their checker.py."""
    if meta.comparator.type is not ComparatorType.CHECKER:
        return comparator_for(meta.comparator)
    if environment.files.read_text(meta.slug, CHECKER_FILE) is None:
        directory = environment.files.problem_directory(meta.slug)
        issue = ContentIssue(f"{directory}/{CHECKER_FILE}", "", "missing (comparator: checker)")
        raise ContentError([issue])
    checker = environment.content_code.checker(environment.files.path(meta.slug, CHECKER_FILE))
    return comparator_for(meta.comparator, checker)
