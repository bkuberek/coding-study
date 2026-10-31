"""`GET /api/v1/stats`: `cstudy stats --json`, with its `by` and `since`
(docs/specs/web-ui.md#mock-progress-and-health)."""

from datetime import date

import pytest

from coding_study.application.environment import Environment
from coding_study.application.show_stats import StatsRequest, show_stats
from coding_study.domain.progress_stats import StatsGrouping
from coding_study.entrypoints.commands.stats import stats_document
from tests.fakes import make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems
from tests.stats_fixture import fill_progress
from tests.web_server import session_client, web_app

STATS = "/api/v1/stats"


@pytest.fixture(scope="module")
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def environment(tmp_path, problems) -> Environment:
    environment = make_environment(repository_root(tmp_path, problems, FIXTURE_TRACKS))
    fill_progress(environment)
    return environment


def get(tmp_path, environment: Environment, query: str = ""):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get(STATS + query)


def test_the_stats_are_cstudy_stats_json(tmp_path, environment):
    expected = stats_document(show_stats(environment, StatsRequest()))
    assert get(tmp_path, environment).json() == expected


def test_by_groups_as_cstudy_stats_by_does(tmp_path, environment):
    expected = stats_document(show_stats(environment, StatsRequest(StatsGrouping.TRACK)))
    assert get(tmp_path, environment, "?by=track").json() == expected


def test_since_narrows_the_attempts_as_cstudy_stats_since_does(tmp_path, environment):
    request = StatsRequest(StatsGrouping.PATTERN, date(2026, 10, 23))
    expected = stats_document(show_stats(environment, request))
    assert get(tmp_path, environment, "?since=2026-10-23").json() == expected


def test_an_unknown_grouping_gets_422(tmp_path, environment):
    assert get(tmp_path, environment, "?by=colour").status_code == 422


def test_a_since_that_is_no_date_gets_the_clis_refusal(tmp_path, environment):
    response = get(tmp_path, environment, "?since=yesterday")
    assert (response.status_code, response.json()["error"]["message"]) == (
        422,
        'invalid --since "yesterday": use a date such as 2026-10-01',
    )
