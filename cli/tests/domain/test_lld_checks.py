"""Static checks (S8) and ready criteria for low-level design problems."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.ready_criteria import ready_problems
from coding_study.domain.static_checks import ProblemContent, static_checks
from tests.fakes import repository_root

PHASE4 = Path(__file__).resolve().parents[1] / "fixtures" / "phase4" / "problems"
PARKING_LOT = PHASE4 / "0002-parking-lot"
RUBRIC_TEXT = (PARKING_LOT / "rubric.md").read_text()
RUBRIC = "problems/0002-parking-lot/rubric.md"


@pytest.fixture(scope="module")
def parking_lot(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PHASE4)
    return FsProblemRepository(root).load("parking-lot")


def content(problem, **changes) -> ProblemContent:
    solutions = PARKING_LOT / "solutions"
    base = ProblemContent(
        directory="problems/0002-parking-lot",
        problem=problem,
        problem_markdown=(PARKING_LOT / "problem.md").read_text(),
        explanation=(solutions / "explanation.md").read_text(),
        files=tuple(sorted(path.name for path in PARKING_LOT.iterdir() if path.is_file())),
        solution_files=tuple(sorted(path.name for path in solutions.iterdir())),
        rubric=RUBRIC_TEXT,
    )
    return replace(base, **changes)


def errors(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).errors]


def test_the_fixture_passes(parking_lot):
    assert errors(content(parking_lot)) == []


def test_the_fixture_is_ready(parking_lot):
    assert ready_problems(content(parking_lot)) == ()


def test_rubric_sections_are_checked(parking_lot):
    rubric = RUBRIC_TEXT.replace("## Testability", "## Tests")
    assert errors(content(parking_lot, rubric=rubric)) == [f'{RUBRIC}: missing "## Testability"']


def test_a_missing_rubric_is_reported_once(parking_lot):
    files = tuple(name for name in content(parking_lot).files if name != "rubric.md")
    assert errors(content(parking_lot, files=files, rubric=None)) == [
        f"{RUBRIC}: missing (track: lld)"
    ]
