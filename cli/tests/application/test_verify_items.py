import shutil
from pathlib import Path

import pytest

from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.problem import Language, Track
from tests.e2e import e2e_environment
from tests.fakes import repository_root
from tests.helpers import FIXTURE_TRACKS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
URL_SHORTENER = "tracks/system-design/url-shortener"
ITEMS = (
    "tracks/code-review/retry-wrapper",
    "tracks/system-design/news-feed",
    URL_SHORTENER,
)


@pytest.fixture
def environment(tmp_path):
    return e2e_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


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


def test_items_follow_the_problems(environment):
    directories = [problem.directory for problem in verify(environment).problems]
    assert directories[2:] == list(ITEMS)


def test_fixture_items_pass(environment):
    assert verify(environment, slugs=("url-shortener", "retry-wrapper")).failed == 0


def test_an_item_can_be_selected_by_slug(environment):
    report = verify(environment, slugs=("url-shortener",))
    assert [problem.directory for problem in report.problems] == [URL_SHORTENER]


def test_unknown_slug_is_still_an_error(environment):
    with pytest.raises(UnknownProblemError):
        verify(environment, slugs=("load-balancer",))


def test_track_filter_selects_items(environment):
    report = verify(environment, track=Track.SYSTEM_DESIGN)
    assert [problem.directory for problem in report.problems] == list(ITEMS[1:])


def test_static_failures_are_reported(environment):
    edit(environment, f"{URL_SHORTENER}/prompt.md", "## Scale", "## Size")
    report = verify(environment, slugs=("url-shortener",))
    assert verified(report, URL_SHORTENER).static_errors == (
        f'{URL_SHORTENER}/prompt.md: missing "## Scale"',
    )


def test_static_item_failures_exit_as_content_errors(environment):
    edit(environment, f"{URL_SHORTENER}/prompt.md", "## Scale", "## Size")
    assert verify(environment, slugs=("url-shortener",)).only_static_failures


def test_invalid_item_yaml_is_a_static_failure(environment):
    (environment.root / URL_SHORTENER / "item.yaml").write_text("slug: url-shortener\n")
    report = verify(environment, slugs=("url-shortener",))
    assert (
        verified(report, URL_SHORTENER)
        .static_errors[0]
        .startswith(f"{URL_SHORTENER}/item.yaml: 'title' is a required property")
    )


def test_require_ready_rejects_drafts(environment):
    report = verify(environment, slugs=("news-feed",), require_ready=True)
    assert report.problems[0].ready_errors == (
        "status is draft, not ready",
        "system-design items need at least one reference (links or study_guides)",
    )


def test_items_run_no_code(environment):
    assert verify(environment, slugs=("url-shortener",), static_only=False).problems[0].passed


def test_unknown_related_slugs_are_warnings(environment):
    edit(environment, f"{URL_SHORTENER}/item.yaml", "[news-feed]", "[news-feed, chat]")
    report = verify(environment, slugs=("url-shortener",))
    assert verified(report, URL_SHORTENER).warnings == (
        f'{URL_SHORTENER}/item.yaml: related: "chat" is not a problem or item (yet)',
    )


def test_problems_may_relate_to_items(environment):
    meta = environment.root / "problems" / "0001-two-sum" / "meta.yaml"
    meta.write_text(meta.read_text() + "related: [url-shortener]\n")
    assert verified(verify(environment), "problems/0001-two-sum").warnings == ()


def test_slug_shared_by_a_problem_and_an_item_fails_both(environment):
    shutil.copytree(
        environment.root / URL_SHORTENER, environment.root / "tracks/system-design/two-sum"
    )
    edit(
        environment,
        "tracks/system-design/two-sum/item.yaml",
        "slug: url-shortener",
        "slug: two-sum",
    )
    report = verify(environment, slugs=("two-sum",))
    assert [problem.static_errors[0] for problem in report.problems] == [
        'problems/0001-two-sum: slug "two-sum" is also used by tracks/system-design/two-sum',
        'tracks/system-design/two-sum: slug "two-sum" is also used by problems/0001-two-sum',
    ]


def test_items_are_not_counted_in_coverage(environment):
    assert [entry.listed for entry in verify(environment).coverage] == [2]
