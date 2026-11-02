"""The generated stress-case table in rendered statements (docs/specs/authoring.md#problemmd)."""

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.problem import Problem
from coding_study.domain.statement import render_statement
from tests.fakes import repository_root
from tests.helpers import CONCURRENCY_PROBLEMS, PROJECT_STRESS_PROBLEMS, TALLY_PROJECT

FIXTURE = CONCURRENCY_PROBLEMS / "0001-bounded-blocking-queue"
TIMES = "\N{MULTIPLICATION SIGN}"
TABLE = [
    "| Stress case | Note | Workers | Checks |",
    "|-------------|------|---------|--------|",
    "| s1 | 4 producers, 4 consumers and a size observer on capacity 4 | "
    f"producer 4 {TIMES} 500, consumer 4 {TIMES} 500, observer 1 {TIMES} 500 | "
    "equal_multisets, distinct, source_order, bounds, final values |",
    "| s2 | capacity 1 forces a hand-off on every op | "
    f"producer 3 {TIMES} 1000 (python 400), consumer 3 {TIMES} 1000 (python 400) | "
    "equal_multisets, source_order, final values |",
]


@pytest.fixture(scope="module")
def problem(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("repository"), CONCURRENCY_PROBLEMS)
    return FsProblemRepository(root).load("bounded-blocking-queue")


def rendered(problem: Problem, markdown: str | None = None) -> list[str]:
    text = (FIXTURE / "problem.md").read_text() if markdown is None else markdown
    return render_statement(problem, text, None).splitlines()


def test_the_table_closes_the_concurrency_section(problem):
    lines = rendered(problem)
    end = lines.index("## Hints") if "## Hints" in lines else len(lines)
    start = lines.index(TABLE[0])
    assert (lines[start : start + len(TABLE)], start < end) == (TABLE, True)


def test_hints_stay_hidden_after_the_table(problem):
    assert "### Hint 1" not in rendered(problem)


def test_the_table_ends_a_statement_whose_last_section_is_concurrency(problem):
    text = (FIXTURE / "problem.md").read_text()
    without_hints = text[: text.index("## Hints")]
    lines = rendered(problem, without_hints)
    assert lines[-len(TABLE) - 2 : -2] == TABLE


# A project's stress cases close the section of their level
# (docs/specs/problem-format.md#statement).

PROJECT_FIXTURE = PROJECT_STRESS_PROBLEMS / TALLY_PROJECT
PROJECT_TABLE = [
    "| Stress case | Note | Workers | Checks |",
    "|-------------|------|---------|--------|",
    f"| s1 | 4 workers add to one key | adder 4 {TIMES} 300 | distinct, final values |",
    f"| s2 | 4 workers take from a stocked key | taker 4 {TIMES} 200 | final values |",
]


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("repository"), PROJECT_STRESS_PROBLEMS)
    return FsProblemRepository(root).load("tally-project-python")


def rendered_project(project: Problem, unlocked: int) -> list[str]:
    text = (PROJECT_FIXTURE / "problem.md").read_text()
    return render_statement(project, text, unlocked).splitlines()


def test_a_project_level_with_stress_cases_ends_with_their_table(project):
    lines = rendered_project(project, 2)
    start = lines.index(PROJECT_TABLE[0])
    level, constraints = lines.index("## Level 2: Shared counts"), lines.index("## Constraints")
    assert lines[start : start + len(PROJECT_TABLE)] == PROJECT_TABLE
    assert level < start < constraints


def test_a_locked_level_shows_no_stress_table(project):
    assert PROJECT_TABLE[0] not in rendered_project(project, 1)


def test_a_level_without_stress_cases_has_no_table(project):
    lines = rendered_project(project, 2)
    assert lines.count(PROJECT_TABLE[0]) == 1
    assert lines.index(PROJECT_TABLE[0]) > lines.index("## Level 2: Shared counts")
