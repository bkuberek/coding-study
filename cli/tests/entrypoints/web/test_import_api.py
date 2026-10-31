"""`POST /api/v1/progress/import`: `cstudy import` from a file the page uploads, after a
confirmation (docs/specs/web-ui.md#mock-progress-and-health)."""

import json
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.progress_backup import export_progress
from tests.fakes import make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems
from tests.stats_fixture import fill_progress
from tests.web_server import WRITE_HEADERS, session_client, web_app

IMPORT = "/api/v1/progress/import"
QUESTION = (
    "Import this file into progress.db? cstudy imports only into a database that holds no "
    "progress yet."
)


@pytest.fixture(scope="module")
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def source(tmp_path, problems) -> Environment:
    environment = make_environment(repository_root(tmp_path / "source", problems, FIXTURE_TRACKS))
    fill_progress(environment)
    return environment


@pytest.fixture
def target(tmp_path, problems) -> Environment:
    return make_environment(repository_root(tmp_path / "target", problems, FIXTURE_TRACKS))


@pytest.fixture
def export(source) -> object:
    return json.loads(export_progress(source).text)


def post(root: Path, environment: Environment, body: object):
    with session_client(web_app(root, environment)) as client:
        return client.post(IMPORT, json=body, headers=WRITE_HEADERS)


def error(response) -> tuple[int, str, str]:
    found = response.json()["error"]
    return response.status_code, found["code"], found["message"]


def test_an_import_needs_a_confirmation(tmp_path, target, export):
    response = post(tmp_path, target, {"export": export})
    assert error(response) == (409, "confirmation_required", QUESTION)


def test_asking_imports_nothing(tmp_path, target, export):
    post(tmp_path, target, {"export": export})
    assert target.progress.snapshot().row_counts()["attempts"] == 0


def test_a_confirmed_import_answers_the_rows_per_table(tmp_path, source, target, export):
    response = post(tmp_path, target, {"confirm": True, "export": export})
    assert response.json() == {"imported": dict(source.progress.snapshot().row_counts())}


def test_a_confirmed_import_restores_every_row(tmp_path, source, target, export):
    post(tmp_path, target, {"confirm": True, "export": export})
    assert target.progress.snapshot() == source.progress.snapshot()


def test_an_import_into_a_database_with_progress_gets_the_clis_refusal(tmp_path, source, export):
    response = post(tmp_path, source, {"confirm": True, "export": export})
    assert error(response)[:2] == (422, "usage")


def test_a_document_that_is_no_export_gets_the_clis_refusal(tmp_path, target):
    response = post(tmp_path, target, {"confirm": True, "export": {"format": "zip"}})
    assert error(response)[:2] == (422, "usage")


def test_an_import_without_an_export_gets_422(tmp_path, target):
    response = post(tmp_path, target, {"confirm": True})
    assert error(response) == (422, "usage", "the request needs export")
