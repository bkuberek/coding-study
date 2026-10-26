"""The generated stress-case table in rendered statements (docs/specs/authoring.md#problemmd)."""

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.problem import Problem
from coding_study.domain.statement import render_statement
from tests.fakes import repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

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
