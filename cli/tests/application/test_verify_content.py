from pathlib import Path

import pytest

from coding_study.application.verify_content import SkippedCheck, VerifyRequest, verify_content
from coding_study.domain.errors import LanguageNotSetUpError, UnknownProblemError
from coding_study.domain.problem import ALL_LANGUAGES, Language, Track
from tests.e2e import e2e_environment
from tests.fakes import repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
TWO_SUM = "problems/0001-two-sum"


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, PRACTICE))


def verify(environment, **fields):
    request = VerifyRequest(**{"language": Language.PYTHON, **fields})
    return verify_content(environment, request, lambda _line: None)


def two_sum(report):
    return next(problem for problem in report.problems if problem.directory == TWO_SUM)


def edit(environment, name: str, old: str, new: str) -> None:
    path = environment.root / TWO_SUM / name
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_every_problem_is_verified(environment):
    report = verify(environment, static_only=True)
    assert [problem.directory for problem in report.problems] == [
        TWO_SUM,
        "problems/0002-lru-cache",
    ]


def test_complete_problems_pass_the_static_checks(environment):
    assert verify(environment, static_only=True).failed == 0


def test_static_failures_are_reported(environment):
    edit(environment, "problem.md", "## Constraints", "## Limits")
    report = verify(environment, static_only=True, slugs=("two-sum",))
    assert two_sum(report).static_errors == (
        'problems/0001-two-sum/problem.md: missing "## Constraints"',
    )


def test_only_static_failures(environment):
    edit(environment, "problem.md", "## Constraints", "## Limits")
    assert verify(environment, slugs=("two-sum",)).only_static_failures


def test_static_failures_skip_running_code(environment):
    edit(environment, "problem.md", "## Constraints", "## Limits")
    assert two_sum(verify(environment, slugs=("two-sum",))).languages == ()


def test_invalid_files_fail_statically_without_stopping_the_others(environment):
    (environment.root / TWO_SUM / "meta.yaml").write_text("id: 1\n")
    report = verify(environment, static_only=True)
    assert [problem.passed for problem in report.problems] == [False, True]


def test_unknown_slug(environment):
    with pytest.raises(UnknownProblemError):
        verify(environment, slugs=("three-sum",))


def test_track_filter(environment):
    assert verify(environment, static_only=True, track=Track.LLD).problems == ()


def test_duplicate_ids_fail(environment):
    copy = environment.root / "problems" / "0001-lru-cache-copy"
    copy.mkdir()
    report = verify(environment, static_only=True, slugs=("two-sum",))
    assert two_sum(report).static_errors == (
        'problems/0001-two-sum: id "0001" is also used by problems/0001-lru-cache-copy',
    )


def test_unknown_related_slugs_are_warnings(environment):
    meta = environment.root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text() + "related: [three-sum]\n")
    report = verify(environment, static_only=True, slugs=("two-sum",))
    assert two_sum(report).warnings == (
        'problems/0001-two-sum/meta.yaml: related: "three-sum" is not a problem (yet)',
    )


def test_references_and_stub_run_per_language(environment):
    result = two_sum(verify(environment, slugs=("two-sum",))).languages[0]
    assert (result.language, result.passing, result.problems) == (Language.PYTHON, 2, ())


def test_failing_reference_is_reported(environment):
    edit(environment, "solutions/brute-force.py", "return [i, j]", "return [j, j]")
    result = two_sum(verify(environment, slugs=("two-sum",))).languages[0]
    assert result.approaches[0].failures[0].startswith("ex1 FAIL: expected [1, 2], got [2, 2]")


def test_broken_stub_is_reported(environment, monkeypatch):
    from tests import e2e

    monkeypatch.setattr(e2e.SimplePythonStubGenerator, "generate", lambda self, meta: "def (:\n")
    result = two_sum(verify(environment, slugs=("two-sum",))).languages[0]
    assert result.problems[0].startswith("stub does not load: SyntaxError")


def test_oracle_agreement(environment):
    report = verify(environment, slugs=("two-sum",), oracle_cases=20)
    oracle = two_sum(report).oracle
    assert oracle is not None
    assert (oracle.agreed, oracle.total, oracle.failures) == (20, 20, ())


def test_oracle_disagreement(environment):
    edit(
        environment,
        "solutions/hash-map.py",
        "return [seen[target - value], index]",
        "return [0, 0]",
    )
    oracle = two_sum(verify(environment, slugs=("two-sum",), oracle_cases=5)).oracle
    assert oracle is not None
    assert (oracle.agreed, oracle.failures[0].split(":")[0]) == (0, "python hash-map oracle-1 FAIL")


def test_oracle_does_not_apply_without_a_generator(environment):
    problem = verify(environment, slugs=("lru-cache",), oracle_cases=5).problems[0]
    assert (problem.oracle, problem.skipped) == (None, (SkippedCheck.ORACLE,))


def test_a_problem_without_a_generator_passes_the_oracle_request(environment):
    assert verify(environment, slugs=("lru-cache",), oracle_cases=5).problems[0].passed


def test_nondeterministic_generator(environment):
    edit(
        environment,
        "generator.py",
        "size = max(n, 2)",
        "import time\n    size = max(n, 2) + int(time.time_ns() % 7)",
    )
    problem = two_sum(verify(environment, slugs=("two-sum",), oracle_cases=3))
    assert any("not deterministic" in error for error in problem.dynamic_errors)


def test_require_ready_reports_missing_criteria(environment):
    problem = two_sum(verify(environment, static_only=True, slugs=("two-sum",), require_ready=True))
    assert "needs at least 8 hidden hand-written cases (has 1)" in problem.ready_errors


def test_coverage_counts_problems_with_a_passing_reference(environment):
    coverage = verify(environment).coverage
    assert [(entry.language, entry.covered, entry.listed) for entry in coverage] == [
        (Language.PYTHON, 2, 2)
    ]


def test_coverage_counts_only_the_problems_that_list_a_language(environment):
    path = environment.root / TWO_SUM / "meta.yaml"
    path.write_text(path.read_text().replace("track: dsa", "track: debugging"))
    path.write_text(path.read_text() + "languages: [python, typescript, java, kotlin]\n")
    coverage = verify(environment, static_only=True, language=None).coverage
    assert [(entry.language, entry.covered, entry.listed) for entry in coverage][-2:] == [
        (Language.GO, 0, 1),
        (Language.RUST, 0, 1),
    ]


def test_verifying_a_listed_language_without_an_adapter_says_it_is_not_set_up(environment):
    with pytest.raises(LanguageNotSetUpError, match="go stub generator is not set up yet"):
        verify(environment, language=Language.GO)


def test_coverage_shows_every_language(environment):
    coverage = verify(environment, static_only=True, language=None).coverage
    assert tuple(entry.language for entry in coverage) == ALL_LANGUAGES


def test_coverage_for_one_language_is_that_language_only(environment):
    coverage = verify(environment, static_only=True, language=Language.RUST).coverage
    assert [(entry.language, entry.covered, entry.listed) for entry in coverage] == [
        (Language.RUST, 0, 2)
    ]


def test_static_coverage_counts_reference_files(environment):
    coverage = verify(environment, static_only=True, language=None).coverage
    assert [(entry.covered, entry.listed) for entry in coverage] == [(2, 2), *[(0, 2)] * 5]
