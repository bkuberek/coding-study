"""`GET /api/v1/progress/export`: the document `cstudy export` writes, as a download
(docs/specs/web-ui.md#mock-progress-and-health)."""

from pathlib import Path

import pytest

from coding_study.application.progress_backup import EXPORT_FILE, export_progress
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.web_server import session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
EXPORT = "/api/v1/progress/export"


@pytest.fixture
def environment(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(repository_root(tmp_path, PRACTICE), toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    return environment


@pytest.fixture
def response(tmp_path, environment):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get(EXPORT)


def test_the_export_is_the_document_cstudy_export_writes(environment, response):
    assert response.text == export_progress(environment).text


def test_the_export_is_a_download_named_as_cstudy_export_names_it(response):
    assert response.headers["content-disposition"] == f'attachment; filename="{EXPORT_FILE}"'


def test_the_export_is_json(response):
    assert (response.status_code, response.headers["content-type"]) == (
        200,
        "application/json; charset=utf-8",
    )


def test_the_export_writes_nothing_in_the_workspace(tmp_path, response):
    assert not (tmp_path / EXPORT_FILE).exists()
