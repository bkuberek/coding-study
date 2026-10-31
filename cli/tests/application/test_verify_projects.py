"""`cstudy verify` on a project problem (docs/specs/authoring.md#project-problems)."""

import shutil
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.verify_content import (
    ProblemVerification,
    VerifyRequest,
    verify_content,
)
from coding_study.domain.problem import Language
from tests.fakes import make_environment, repository_root
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS

SLUG = "bank-project-python"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PROJECT_PROBLEMS)


@pytest.fixture
def environment(root: Path) -> Environment:
    return make_environment(root)


def verify(environment: Environment, **fields: object) -> ProblemVerification:
    request = VerifyRequest(**{"slugs": (SLUG,), **fields})  # type: ignore[arg-type]
    [problem] = verify_content(environment, request, lambda _line: None).problems
    return problem


def coverage(environment: Environment, language: Language) -> tuple[int, int]:
    request = VerifyRequest(slugs=(SLUG,), static_only=True)
    report = verify_content(environment, request, lambda _line: None)
    [entry] = (entry for entry in report.coverage if entry.language is language)
    return entry.covered, entry.listed


def test_a_projects_reference_language_is_its_overlays(environment):
    assert verify(environment, static_only=True).reference_languages == (Language.PYTHON,)


def test_a_project_without_an_overlay_has_no_reference_language(environment, root):
    shutil.rmtree(root / "problems" / BANK_PROJECT / "solutions" / "reference")
    assert verify(environment, static_only=True).reference_languages == ()


def test_a_project_counts_towards_the_coverage_of_its_language(environment):
    assert coverage(environment, Language.PYTHON) == (1, 1)


def test_a_project_is_not_listed_under_other_languages(environment):
    assert coverage(environment, Language.TYPESCRIPT) == (0, 0)
