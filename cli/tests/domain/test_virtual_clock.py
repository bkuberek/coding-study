"""Which languages can declare `project.clock` and `async` (check S18's declarations,
docs/specs/authoring.md#what-cstudy-verify-checks)."""

from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain import virtual_clock
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.project import Project
from coding_study.domain.signature import ClassSignature, SignatureIssue
from coding_study.domain.virtual_clock import (
    ASYNC_LANGUAGES,
    CLOCK_LANGUAGES,
    GRADED_CLOCK_LANGUAGES,
    ProjectClock,
    clock_declaration_issues,
)
from tests.fakes import repository_root
from tests.helpers import PROJECT_PROBLEMS

CLOCK_LOCATION = "project.clock"
FIRST_METHOD_ASYNC = "signature.class.methods[0].async"


@pytest.fixture(scope="module")
def bank_meta(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-python").meta


def declared(meta, language: Language, *, clock: bool, async_methods: tuple[int, ...] = ()):
    """`meta` as a project in `language`, with the virtual clock when `clock`, and the methods at
    `async_methods` asynchronous."""
    assert isinstance(meta.signature, ClassSignature)
    methods = tuple(
        replace(method, is_async=index in async_methods)
        for index, method in enumerate(meta.signature.methods)
    )
    project = Project("bank.bank", clock=ProjectClock.VIRTUAL if clock else None)
    return replace(
        meta,
        languages=(language,),
        project=project,
        signature=replace(meta.signature, methods=methods),
    )


def test_the_languages_with_a_virtual_clock_are_go_python_typescript_kotlin_and_rust():
    assert CLOCK_LANGUAGES == (
        Language.GO,
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.KOTLIN,
        Language.RUST,
    )


def test_the_languages_with_awaitable_methods_are_those_with_a_clock_but_go():
    assert set(ASYNC_LANGUAGES) == set(CLOCK_LANGUAGES) - {Language.GO}


def test_the_go_runner_grades_the_virtual_clock():
    """Each runner that lands adds its language here, with its runner's `clock` feature."""
    assert sorted(GRADED_CLOCK_LANGUAGES) == [Language.GO]


def test_a_go_project_can_declare_the_virtual_clock(bank_meta):
    assert clock_declaration_issues(declared(bank_meta, Language.GO, clock=True)) == ()


def test_a_go_project_on_the_clock_still_has_no_async_methods(bank_meta):
    meta = declared(bank_meta, Language.GO, clock=True, async_methods=(0,))
    assert [issue.location for issue in clock_declaration_issues(meta)] == [FIRST_METHOD_ASYNC]


def test_the_real_clock_is_the_default():
    assert Project("bank.bank").clock is None


def test_the_only_clock_a_project_declares_is_virtual():
    assert [clock.value for clock in ProjectClock] == ["virtual"]


@pytest.mark.usefixtures("graded_clock_runners")
@pytest.mark.parametrize("language", CLOCK_LANGUAGES)
def test_a_language_with_a_graded_clock_can_declare_it(bank_meta, language):
    assert clock_declaration_issues(declared(bank_meta, language, clock=True)) == ()


@pytest.mark.usefixtures("graded_clock_runners")
def test_java_has_no_virtual_clock(bank_meta):
    meta = declared(bank_meta, Language.JAVA, clock=True)
    assert clock_declaration_issues(meta) == (
        SignatureIssue(
            CLOCK_LOCATION,
            '"virtual" is for go, python, typescript, kotlin and rust projects, not java',
        ),
    )


@pytest.mark.parametrize(
    "language", [language for language in CLOCK_LANGUAGES if language is not Language.GO]
)
def test_a_declaration_waits_for_the_runner_that_grades_it(bank_meta, language):
    meta = declared(bank_meta, language, clock=True)
    assert clock_declaration_issues(meta) == (
        SignatureIssue(
            CLOCK_LOCATION, f"the {language} runner does not grade the virtual clock yet"
        ),
    )


def test_a_runner_that_lands_opens_its_language_alone(bank_meta, monkeypatch):
    graded = frozenset({Language.GO, Language.PYTHON})
    monkeypatch.setattr(virtual_clock, "GRADED_CLOCK_LANGUAGES", graded)
    opened = clock_declaration_issues(declared(bank_meta, Language.PYTHON, clock=True))
    waiting = clock_declaration_issues(declared(bank_meta, Language.TYPESCRIPT, clock=True))
    assert (opened, len(waiting)) == ((), 1)


def test_a_project_on_the_real_clock_declares_nothing(bank_meta):
    assert clock_declaration_issues(declared(bank_meta, Language.JAVA, clock=False)) == ()


@pytest.mark.usefixtures("graded_clock_runners")
@pytest.mark.parametrize("language", ASYNC_LANGUAGES)
def test_a_method_can_be_async_in_a_language_whose_methods_return_an_awaitable(bank_meta, language):
    meta = declared(bank_meta, language, clock=True, async_methods=(0, 2))
    assert clock_declaration_issues(meta) == ()


@pytest.mark.usefixtures("graded_clock_runners")
def test_a_go_method_blocks_instead_of_returning_an_awaitable(bank_meta):
    meta = declared(bank_meta, Language.GO, clock=True, async_methods=(0,))
    assert clock_declaration_issues(meta) == (
        SignatureIssue(
            FIRST_METHOD_ASYNC,
            "only python, typescript, kotlin and rust methods can be async, not go's",
        ),
    )


@pytest.mark.usefixtures("graded_clock_runners")
def test_a_java_method_cannot_be_async(bank_meta):
    meta = declared(bank_meta, Language.JAVA, clock=False, async_methods=(1,))
    assert [issue.location for issue in clock_declaration_issues(meta)] == [
        "signature.class.methods[1].async"
    ]


@pytest.mark.usefixtures("graded_clock_runners")
def test_an_async_method_needs_the_virtual_clock(bank_meta):
    meta = declared(bank_meta, Language.PYTHON, clock=False, async_methods=(0,))
    assert clock_declaration_issues(meta) == (
        SignatureIssue(
            FIRST_METHOD_ASYNC,
            "needs project.clock: virtual, since a real clock would wait for real",
        ),
    )


@pytest.mark.usefixtures("graded_clock_runners")
def test_every_async_method_is_reported_at_its_own_position(bank_meta):
    meta = declared(bank_meta, Language.PYTHON, clock=False, async_methods=(0, 2))
    assert [issue.location for issue in clock_declaration_issues(meta)] == [
        "signature.class.methods[0].async",
        "signature.class.methods[2].async",
    ]


def test_another_kind_of_problem_declares_nothing_here(bank_meta):
    meta = replace(declared(bank_meta, Language.PYTHON, clock=True), kind=ProblemKind.DESIGN)
    assert clock_declaration_issues(meta) == ()


def test_a_project_that_lists_two_languages_is_left_to_s14(bank_meta):
    meta = replace(
        declared(bank_meta, Language.JAVA, clock=True),
        languages=(Language.JAVA, Language.PYTHON),
    )
    assert clock_declaration_issues(meta) == ()
