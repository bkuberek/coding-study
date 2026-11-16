"""`cstudy verify` skips a language whose program is missing and verifies the others; the ready
gate counts the skip as not passed; `--skip-lang` leaves a language out, uncounted
(docs/specs/cli.md#cstudy-verify)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import repository_root, without

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
NO_NODE = "node was not found on PATH"
TYPESCRIPT = Language.TYPESCRIPT
OTHERS = (Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST)


@pytest.fixture
def environment(tmp_path):
    """Two Sum, with no `node` on the machine and only Python and TypeScript left to verify."""
    return replace(
        e2e_environment(repository_root(tmp_path, PRACTICE)), toolchain_check=without("node")
    )


def verify(environment, **fields):
    request = VerifyRequest(**{"slugs": ("two-sum",), "skip_languages": OTHERS, **fields})
    [problem] = verify_content(environment, request, lambda _line: None).problems
    return problem


def test_the_languages_with_their_programs_still_verify(environment):
    problem = verify(environment)
    assert [(r.language, r.skipped, r.passing) for r in problem.languages] == [
        (Language.PYTHON, None, 2),
        (TYPESCRIPT, NO_NODE, 0),
    ]


def test_a_missing_program_is_no_failure(environment):
    assert verify(environment).passed


def test_a_skipped_language_is_not_covered(environment):
    assert not verify(environment).covers(TYPESCRIPT)


def test_the_ready_gate_counts_the_skip_as_not_passed(environment):
    problem = verify(environment, require_ready=True)
    assert f"typescript skipped: {NO_NODE}" in problem.ready_errors
    assert not problem.passed


def test_without_the_ready_gate_nothing_is_added_for_the_skip(environment):
    assert not any("skipped" in error for error in verify(environment).ready_errors)


def test_a_language_left_out_by_skip_lang_is_not_in_the_result(environment):
    problem = verify(environment, skip_languages=(*OTHERS, TYPESCRIPT))
    assert [r.language for r in problem.languages] == [Language.PYTHON]


def test_a_language_left_out_by_skip_lang_is_not_counted_by_the_ready_gate(environment):
    problem = verify(environment, require_ready=True, skip_languages=(*OTHERS, TYPESCRIPT))
    assert not any("skipped" in error for error in problem.ready_errors)


def test_a_language_left_out_by_skip_lang_is_not_skipped_for_its_program(environment):
    problem = verify(environment, skip_languages=(*OTHERS, TYPESCRIPT))
    assert all(result.skipped is None for result in problem.languages)


def test_skip_lang_leaves_the_language_out_of_the_coverage(environment):
    request = VerifyRequest(
        slugs=("two-sum",), static_only=True, skip_languages=(Language.PYTHON, TYPESCRIPT)
    )
    report = verify_content(environment, request, lambda _line: None)
    assert [entry.language for entry in report.coverage] == list(OTHERS)
