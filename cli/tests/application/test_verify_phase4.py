"""`cstudy verify` on the Phase 4 fixtures: a progressive problem and a low-level design problem."""

from pathlib import Path

import pytest

from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import repository_root

PHASE4 = Path(__file__).resolve().parents[1] / "fixtures" / "phase4" / "problems"
LEVEL_STORE = "problems/0001-level-store"


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, PHASE4))


def verify(environment, **fields):
    request = VerifyRequest(**{"language": Language.PYTHON, "require_ready": True, **fields})
    return verify_content(environment, request, lambda _line: None)


def level_store(report):
    return next(problem for problem in report.problems if problem.directory == LEVEL_STORE)


def test_the_fixtures_are_ready_and_pass(environment):
    assert verify(environment).failed == 0


def test_reference_failures_name_their_level(environment):
    reference = environment.root / LEVEL_STORE / "solutions" / "hash-map.py"
    text = reference.read_text()
    reference.write_text(text.replace("return len(self._values)", "return 0"))
    python = level_store(verify(environment, slugs=("level-store",))).languages[0]
    assert python.approaches[0].failures[0] == (
        'level 2 ex2 FAIL: expected [null, null, null, 2, true, false, "", 1], '
        'got [null, null, null, 0, true, false, "", 0] (op 3 size: expected 2, got 0)'
    )
