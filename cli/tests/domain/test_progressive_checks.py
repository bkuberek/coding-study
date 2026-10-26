"""Static checks (S5, S10) and ready criteria for progressive problems."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case, GeneratedInput
from coding_study.domain.problem import Level
from coding_study.domain.ready_criteria import ready_problems
from coding_study.domain.static_checks import ProblemContent, static_checks
from tests.fakes import repository_root

PHASE4 = Path(__file__).resolve().parents[1] / "fixtures" / "phase4" / "problems"
LEVEL_STORE = PHASE4 / "0001-level-store"
PROBLEM = "problems/0001-level-store/problem.md"
TESTS = "problems/0001-level-store/tests.json"


@pytest.fixture(scope="module")
def level_store(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PHASE4)
    return FsProblemRepository(root).load("level-store")


def content(problem, **changes) -> ProblemContent:
    solutions = LEVEL_STORE / "solutions"
    base = ProblemContent(
        directory="problems/0001-level-store",
        problem=problem,
        problem_markdown=(LEVEL_STORE / "problem.md").read_text(),
        explanation=(solutions / "explanation.md").read_text(),
        files=tuple(sorted(path.name for path in LEVEL_STORE.iterdir() if path.is_file())),
        solution_files=tuple(sorted(path.name for path in solutions.iterdir())),
    )
    return replace(base, **changes)


def errors(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).errors]


def edited_markdown(old: str, new: str) -> str:
    text = (LEVEL_STORE / "problem.md").read_text()
    assert old in text
    return text.replace(old, new)


def with_levels(problem, *titles: str):
    levels = tuple(Level(number, title) for number, title in enumerate(titles, start=1))
    return replace(problem, meta=replace(problem.meta, levels=levels))


def with_case_changes(problem, case_id: str, **changes):
    cases = tuple(
        replace(case, **changes) if case.id == case_id else case for case in problem.cases
    )
    return replace(problem, cases=cases)


def test_the_fixture_passes(level_store):
    assert errors(content(level_store)) == []


def test_the_fixture_is_ready(level_store):
    assert ready_problems(content(level_store)) == ()


# S5


def test_examples_go_in_level_sections_not_in_an_examples_section(level_store):
    markdown = edited_markdown("## Constraints", "## Examples\n\nNone.\n\n## Constraints")
    assert f'{PROBLEM}: progressive problems put examples in "## Level" sections, not in ' in (
        "\n".join(errors(content(level_store, problem_markdown=markdown)))
    )


def test_an_example_belongs_in_its_own_level_section(level_store):
    markdown = edited_markdown("<!-- case: ex2 -->", "<!-- case: ex1 -->").replace(
        "<!-- case: ex1 -->", "<!-- case: ex2 -->", 1
    )
    assert errors(content(level_store, problem_markdown=markdown)) == [
        f'{PROBLEM}: case "ex2" is a level 2 example but sits in "## Level 1: Put and get"',
        f'{PROBLEM}: case "ex1" is a level 1 example but sits in "## Level 2: Remove and size"',
    ]


def test_an_example_outside_the_level_sections_is_misplaced(level_store):
    markdown = edited_markdown(
        "## Input", "### Example 1\n\n<!-- case: ex3 -->\n\nEarly.\n\n## Input"
    ).replace("### Example 1\n\n<!-- case: ex3 -->\n\nTwo keys", "Two keys")
    assert errors(content(level_store, problem_markdown=markdown)) == [
        f'{PROBLEM}: "## Level 3: Prefix scans" needs at least one "### Example <n>"',
        f'{PROBLEM}: case "ex3" is a level 3 example but sits outside the "## Level" sections',
    ]


def test_level_sections_follow_the_meta_titles(level_store):
    problem = with_levels(level_store, "Put and get", "Delete", "Prefix scans")
    assert errors(content(problem)) == [
        f'{PROBLEM}: "## Level 2: Remove and size" must be titled "## Level 2: Delete"'
    ]


def test_a_level_section_needs_a_declared_level(level_store):
    markdown = edited_markdown("## Constraints", "## Level 4: Extra\n\nMore.\n\n## Constraints")
    assert errors(content(level_store, problem_markdown=markdown)) == [
        f'{PROBLEM}: "## Level 4: Extra" names no level in meta.yaml'
    ]


def test_level_sections_are_in_level_order(level_store):
    text = (LEVEL_STORE / "problem.md").read_text()
    start, middle = text.index("## Level 1"), text.index("## Level 2")
    end = text.index("## Level 3")
    markdown = text[:start] + text[middle:end] + text[start:middle] + text[end:]
    assert errors(content(level_store, problem_markdown=markdown)) == [
        f'{PROBLEM}: "## Level" sections must be in level order: 1, 2, 3'
    ]


# S10


def test_every_level_needs_a_case(level_store):
    cases = tuple(case for case in level_store.cases if case.level != 3)
    assert f"{TESTS}: level 3 has no cases" in errors(content(replace(level_store, cases=cases)))


def test_generate_cases_belong_to_the_last_level(level_store):
    generated = Case("g1", GeneratedInput(10, 1), level=2)
    problem = replace(level_store, cases=(*level_store.cases, generated))
    assert f"{TESTS}: cases[12] g1: a generate case belongs to the last level (3)" in errors(
        content(problem)
    )


# ready criteria


def test_every_level_needs_a_visible_case(level_store):
    problem = with_case_changes(level_store, "ex2", visible=False)
    assert "level 2 needs at least 1 visible case (has 0)" in ready_problems(content(problem))


def test_every_level_needs_two_hidden_cases(level_store):
    cases = tuple(case for case in level_store.cases if case.id not in ("h7", "h8"))
    problem = replace(level_store, cases=cases)
    assert "level 3 needs at least 2 hidden hand-written cases (has 1)" in ready_problems(
        content(problem)
    )


def test_a_progressive_problem_needs_two_levels(level_store):
    problem = with_levels(level_store, "Put and get")
    assert "progressive problems need at least 2 levels" in ready_problems(content(problem))


def test_without_a_generator_no_generate_case_is_needed(level_store):
    assert not any("generate case" in reason for reason in ready_problems(content(level_store)))
