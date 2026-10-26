"""`cstudy solution` on a low-level design problem: the rubric, the reference design, then code."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.reveal_solution import SolutionRequest, show_solution
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import solution
from tests.fakes import make_environment
from tests.fakes import repository_root as copy_repository

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(copy_repository(tmp_path, PHASE4))
    monkeypatch.setattr(solution, "load_environment", lambda *_: environment)
    return environment


def output(*arguments: str) -> str:
    return runner.invoke(cli.app, ["--no-color", "solution", *arguments]).output


def test_the_view_carries_the_rubric(environment):
    view = show_solution(environment, SolutionRequest("parking-lot"))
    assert str(view.rubric).startswith("# Parking Lot: Rubric")


def test_problems_without_a_rubric_have_none(environment):
    assert show_solution(environment, SolutionRequest("level-store")).rubric is None


def test_shows_the_design_criteria(environment):
    assert "alone decides which spot a car gets" in output("parking-lot")


def test_shows_the_reference_design(environment):
    assert "keeps an occupancy array indexed by spot number" in output("parking-lot")


def test_the_rubric_comes_before_the_code(environment):
    shown = output("parking-lot", "--lang", "java")
    assert shown.index("Reference design") < shown.index("public int park(String plate)")


def test_explanation_only_still_shows_the_rubric(environment):
    assert "Reference design" in output("parking-lot", "--explanation-only")
