from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case, Expected, FunctionInput, GeneratedInput
from coding_study.domain.comparators import comparator_for
from coding_study.domain.conformance import ExpectedOutcome, ExpectedStatus
from coding_study.domain.conformance_check import outcome_mismatch
from coding_study.domain.judging import RunnableCase, judge, verdict_summary
from coding_study.domain.layout import reference_file_name
from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    ContentStatus,
    Language,
)
from coding_study.domain.ready_criteria import ready_problems
from coding_study.domain.runs import (
    CaseReport,
    InvalidOutput,
    JobReport,
    Raised,
    Returned,
    TimedOut,
    UserError,
)
from coding_study.domain.static_checks import ProblemContent
from coding_study.domain.stub_check import stub_as_reference
from tests.fakes import repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
EXACT = comparator_for(ComparatorSpec(ComparatorType.EXACT))
CASE = RunnableCase("c1", FunctionInput({"value": 1}), Expected(1))


def verdict(outcome, case=CASE):
    return judge([case], JobReport("job", (CaseReport(case.id, outcome),)), EXACT).verdicts[0]


# conformance outcomes


@pytest.mark.parametrize(
    ("expected", "outcome"),
    [
        (ExpectedOutcome(ExpectedStatus.PASS), Returned(1, 5)),
        (ExpectedOutcome(ExpectedStatus.PASS, stdout="hi\n"), Returned(1, 5, "hi\n")),
        (ExpectedOutcome(ExpectedStatus.ERROR), Raised(UserError("E", "boom"), 5)),
        (
            ExpectedOutcome(ExpectedStatus.ERROR, "boom", 3, (None, 1)),
            Raised(UserError("E", "boom"), 5, op_index=3, partial_output=(None, 1)),
        ),
        (ExpectedOutcome(ExpectedStatus.INVALID_OUTPUT), InvalidOutput("cyclic", 5)),
        (ExpectedOutcome(ExpectedStatus.TIMEOUT), TimedOut(500)),
    ],
)
def test_matching_outcomes(expected, outcome):
    assert outcome_mismatch(expected, verdict(outcome)) is None


@pytest.mark.parametrize(
    ("expected", "outcome", "message"),
    [
        (ExpectedOutcome(ExpectedStatus.PASS), Returned(2, 5), "expected pass, got FAIL"),
        (
            ExpectedOutcome(ExpectedStatus.PASS, stdout="hi\n"),
            Returned(1, 5, "ho\n"),
            'expected stdout "hi\\n", got "ho\\n"',
        ),
        (ExpectedOutcome(ExpectedStatus.ERROR), Returned(1, 5), "expected error, got PASS"),
        (
            ExpectedOutcome(ExpectedStatus.ERROR, "boom"),
            Raised(UserError("E", "bang"), 5),
            'expected message "boom", got "bang"',
        ),
        (
            ExpectedOutcome(ExpectedStatus.ERROR, op_index=3),
            Raised(UserError("E", "m"), 5, op_index=2),
            "expected op_index 3, got 2",
        ),
        (
            ExpectedOutcome(ExpectedStatus.ERROR, partial_output=(None, 1)),
            Raised(UserError("E", "m"), 5, partial_output=(None,)),
            "expected partial_output [null, 1], got [null]",
        ),
        (ExpectedOutcome(ExpectedStatus.TIMEOUT), Returned(1, 5), "expected timeout, got PASS"),
        (
            ExpectedOutcome(ExpectedStatus.INVALID_OUTPUT),
            Returned(1, 5),
            "expected invalid_output, got PASS",
        ),
        (ExpectedOutcome(ExpectedStatus.LOAD_ERROR), Returned(1, 5), "expected load_error"),
    ],
)
def test_mismatched_outcomes(expected, outcome, message):
    mismatch = outcome_mismatch(expected, verdict(outcome))
    assert mismatch is not None
    assert mismatch.startswith(message)


# verdict summaries


def test_wrong_answer_summary():
    assert verdict_summary(verdict(Returned(2, 5))) == "c1 FAIL: expected 1, got 2"


def test_error_summary():
    summary = verdict_summary(verdict(Raised(UserError("KeyError", "3"), 5)))
    assert summary == "c1 ERROR: KeyError: 3"


def test_passing_summary():
    assert verdict_summary(verdict(Returned(1, 5))) == "c1 PASS"


# stubs as references


def test_jvm_stubs_lose_their_package_line():
    java = "package practice.two_sum;\n\nimport java.util.*;\n\npublic class Solution {}\n"
    assert (
        stub_as_reference(java, Language.JAVA)
        == "\nimport java.util.*;\n\npublic class Solution {}\n"
    )


def test_kotlin_package_lines_have_no_semicolon():
    kotlin = "package practice.two_sum\n\nclass Solution\n"
    assert stub_as_reference(kotlin, Language.KOTLIN) == "\nclass Solution\n"


def test_python_stubs_are_unchanged():
    assert stub_as_reference("def f():\n    pass\n", Language.PYTHON) == "def f():\n    pass\n"


# ready criteria


@pytest.fixture(scope="module")
def two_sum(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PRACTICE)
    return FsProblemRepository(root).load("two-sum")


def ready_content(problem, **changes) -> ProblemContent:
    directory = PRACTICE / "0001-two-sum"
    references = tuple(
        reference_file_name(approach.id, language)
        for approach in problem.meta.approaches
        for language in problem.meta.languages
    )
    base = ProblemContent(
        directory="problems/0001-two-sum",
        problem=problem,
        problem_markdown=None,
        explanation=None,
        files=tuple(sorted(path.name for path in directory.iterdir() if path.is_file())),
        solution_files=("explanation.md", *references),
    )
    return replace(base, **changes)


def hidden_cases(count: int) -> tuple[Case, ...]:
    return tuple(
        Case(f"h{index}", FunctionInput({"nums": [1, 2], "target": 3}), Expected([0, 1]))
        for index in range(10, 10 + count)
    )


def with_cases(problem, *cases):
    return replace(problem, cases=(*problem.cases, *cases))


def test_a_complete_problem_is_ready(two_sum):
    problem = with_cases(two_sum, *hidden_cases(7), Case("g9", GeneratedInput(100, 2)))
    assert ready_problems(ready_content(problem)) == ()


def test_draft_status_is_not_ready(two_sum):
    problem = replace(two_sum, meta=replace(two_sum.meta, status=ContentStatus.DRAFT))
    assert "status is draft, not ready" in ready_problems(ready_content(problem))


def test_every_language_needs_an_optimal_reference(two_sum):
    files = ("brute-force.py", "hash-map.py")
    problems = ready_problems(ready_content(two_sum, solution_files=files))
    assert "no optimal reference in typescript, java, kotlin" in problems


def test_every_approach_needs_a_reference_in_every_language(two_sum):
    files = tuple(
        name for name in ready_content(two_sum).solution_files if name != "brute-force.kt"
    )
    problems = ready_problems(ready_content(two_sum, solution_files=files))
    assert "brute-force has no reference in kotlin" in problems


def test_an_approach_needs_references_only_in_its_languages(two_sum):
    brute = replace(two_sum.meta.approaches[0], languages=(Language.PYTHON,))
    meta = replace(two_sum.meta, approaches=(brute, *two_sum.meta.approaches[1:]))
    files = (*(name for name in ready_content(two_sum).solution_files if "brute" not in name),)
    content = ready_content(replace(two_sum, meta=meta), solution_files=(*files, "brute-force.py"))
    assert not any("brute-force" in problem for problem in ready_problems(content))


def test_hand_written_hidden_cases_are_counted(two_sum):
    assert "needs at least 8 hidden hand-written cases (has 1)" in ready_problems(
        ready_content(two_sum)
    )


def test_needs_a_generate_case_at_the_largest_ladder_size(two_sum):
    problem = with_cases(two_sum, *hidden_cases(7))
    larger = replace(problem.meta, perf=replace(problem.meta.perf, size_ladder=(10, 1000)))
    problems = ready_problems(ready_content(replace(problem, meta=larger)))
    assert problems == ("needs a generate case at the largest ladder size (n=1000)",)


def test_dsa_problems_need_a_generator(two_sum):
    files = tuple(name for name in ready_content(two_sum).files if name != "generator.py")
    assert "dsa problems need generator.py" in ready_problems(ready_content(two_sum, files=files))
