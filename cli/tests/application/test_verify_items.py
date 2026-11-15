from pathlib import Path

import pytest

from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.problem import Language, Track
from tests.e2e import e2e_environment
from tests.fakes import repository_root
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
URL_SHORTENER = "problems/url-shortener"
RUBRIC_PROBLEMS = (
    "problems/news-feed",
    "problems/retry-wrapper",
    URL_SHORTENER,
)


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS))


def verify(environment, **fields):
    request = VerifyRequest(**{"language": Language.PYTHON, "static_only": True, **fields})
    return verify_content(environment, request, lambda _line: None)


def verified(report, directory: str):
    return next(problem for problem in report.problems if problem.directory == directory)


def edit(environment, relative: str, old: str, new: str) -> None:
    path = environment.root / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_rubric_problems_follow_the_problems(environment):
    directories = [problem.directory for problem in verify(environment).problems]
    assert directories == ["problems/lru-cache", "problems/two-sum", *RUBRIC_PROBLEMS]


def test_a_rubric_problem_is_not_loaded_as_an_autograded_one(environment):
    report = verify(environment, slugs=("url-shortener", "two-sum"))
    assert [problem.meta is not None for problem in report.problems] == [True, False]


def test_fixture_rubric_problems_pass(environment):
    assert verify(environment, slugs=("url-shortener", "retry-wrapper")).failed == 0


def test_a_rubric_problem_can_be_selected_by_slug(environment):
    report = verify(environment, slugs=("url-shortener",))
    assert [problem.directory for problem in report.problems] == [URL_SHORTENER]


def test_unknown_slug_is_still_an_error(environment):
    with pytest.raises(UnknownProblemError):
        verify(environment, slugs=("load-balancer",))


def test_track_filter_selects_rubric_problems(environment):
    report = verify(environment, track=Track.SYSTEM_DESIGN)
    assert [problem.directory for problem in report.problems] == [
        "problems/news-feed",
        URL_SHORTENER,
    ]


def test_static_failures_are_reported(environment):
    edit(environment, f"{URL_SHORTENER}/prompt.md", "## Scale", "## Size")
    report = verify(environment, slugs=("url-shortener",))
    assert verified(report, URL_SHORTENER).static_errors == (
        f'{URL_SHORTENER}/prompt.md: missing "## Scale"',
    )


def test_static_rubric_problem_failures_exit_as_content_errors(environment):
    edit(environment, f"{URL_SHORTENER}/prompt.md", "## Scale", "## Size")
    assert verify(environment, slugs=("url-shortener",)).only_static_failures


def test_invalid_rubric_problem_meta_is_a_static_failure(environment):
    (environment.root / URL_SHORTENER / "meta.yaml").write_text(
        "slug: url-shortener\nkind: system-design\n"
    )
    report = verify(environment, slugs=("url-shortener",))
    assert (
        verified(report, URL_SHORTENER)
        .static_errors[0]
        .startswith(f"{URL_SHORTENER}/meta.yaml: 'estimate_minutes' is a required property")
    )


def test_require_ready_rejects_drafts(environment):
    report = verify(environment, slugs=("news-feed",), require_ready=True)
    assert report.problems[0].ready_errors == (
        "status is draft, not ready",
        "system-design problems need at least one reference (links or study_guides)",
    )


def test_rubric_problems_run_no_code(environment):
    assert verify(environment, slugs=("url-shortener",), static_only=False).problems[0].passed


def test_unknown_related_slugs_are_warnings(environment):
    edit(environment, f"{URL_SHORTENER}/meta.yaml", "[news-feed]", "[news-feed, chat]")
    report = verify(environment, slugs=("url-shortener",))
    assert verified(report, URL_SHORTENER).warnings == (
        f'{URL_SHORTENER}/meta.yaml: related: "chat" is not a problem (yet)',
    )


def test_problems_may_relate_to_rubric_problems(environment):
    meta = environment.root / "problems" / "two-sum" / "meta.yaml"
    meta.write_text(meta.read_text() + "related: [url-shortener]\n")
    assert verified(verify(environment), "problems/two-sum").warnings == ()


def test_rubric_problems_are_not_counted_in_coverage(environment):
    assert [entry.listed for entry in verify(environment).coverage] == [2]
