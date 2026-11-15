"""`/api/v1/docs` (docs/specs/user-docs.md#docs-view): the documents of `cstudy docs --json`, each
page with its passages for the Docs view's search, and a page's HTML with an id on each heading
and its links to other pages turned into the view's routes."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.domain.content_ids import ContentType
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import docs
from coding_study.entrypoints.web.markdown import render_doc_markdown
from tests.content_id_checks import content_ids_in
from tests.doc_builders import write_docs
from tests.fakes import make_environment
from tests.web_server import session_client, web_app

DOCS = "/api/v1/docs"
runner = CliRunner()


@pytest.fixture
def environment(content_root: Path) -> Environment:
    write_docs(content_root)
    return make_environment(content_root)


@pytest.fixture
def client(tmp_path: Path, environment: Environment):
    with session_client(web_app(tmp_path / "server", environment)) as opened:
        yield opened


def cli_document(monkeypatch: pytest.MonkeyPatch, environment: Environment, *arguments: str):
    monkeypatch.setattr(docs, "load_catalog_environment", lambda *_: environment)
    return json.loads(runner.invoke(cli.app, ["docs", *arguments, "--json"]).stdout)


def test_the_list_is_the_document_of_cstudy_docs_with_each_pages_passages(
    client, monkeypatch, environment
):
    listing = client.get(DOCS).json()
    passages = [page.pop("passages") for page in listing["pages"]]
    assert (listing, passages[1]) == (
        cli_document(monkeypatch, environment),
        [
            {
                "id": "",
                "title": "Check your setup",
                "text": "What cstudy doctor checks. It checks each tool.",
            },
            {"id": "the-rows", "title": "The rows", "text": "One per tool."},
            {"id": "--fix", "title": "--fix", "text": "It sets up the workspace."},
        ],
    )


def test_a_page_is_the_document_of_cstudy_docs_with_its_html(client, monkeypatch, environment):
    document = client.get(f"{DOCS}/getting-started").json()
    html = document.pop("html")
    assert (document, html.startswith("<p>")) == (
        cli_document(monkeypatch, environment, "getting-started"),
        True,
    )


def test_every_page_has_the_id_of_its_slug(client):
    assert client.get(f"{DOCS}/getting-started").json()["id"] == "doc/getting-started"
    assert {ContentType.DOC} == {kind for kind, _ in content_ids_in(client.get(DOCS).json())}


def test_an_unknown_topic_is_not_found_with_the_clis_message(client):
    response = client.get(f"{DOCS}/doctr")
    assert (response.status_code, response.json()["error"]["message"]) == (
        404,
        'unknown topic "doctr"; did you mean doctor?',
    )


def test_the_html_has_no_title_and_an_id_on_each_heading():
    html = render_doc_markdown(
        "# Doctor\n\nIntro.\n\n## The rows\n\n## The rows\n\n### `--fix`\n", "doctor"
    )
    assert html == (
        "<p>Intro.</p>\n"
        '<h2 id="doc-the-rows">The rows</h2>\n'
        '<h2 id="doc-the-rows-1">The rows</h2>\n'
        '<h3 id="doc---fix"><code>--fix</code></h3>\n'
    )


def test_links_to_pages_and_headings_become_routes_of_the_view_and_web_links_open_elsewhere():
    html = render_doc_markdown(
        "# D\n\n[a](toolchains.md), [b](toolchains.md#jdk), [c](#the-rows), "
        "[d](https://example.org), [e](../docs/specs/cli.md), ![f](x.png)\n",
        "doctor",
    )
    assert html == (
        '<p><a href="#/docs/toolchains">a</a>, <a href="#/docs/toolchains/jdk">b</a>, '
        '<a href="#/docs/doctor/the-rows">c</a>, '
        '<a href="https://example.org" rel="noopener noreferrer" target="_blank">d</a>, e, f</p>\n'
    )


def test_code_is_highlighted_and_html_stays_text():
    html = render_doc_markdown("# D\n\n```python\nprint(1)\n```\n\n<b>bold</b>\n", "doctor")
    assert ('class="tok-' in html, "<b>" in html, "&lt;b&gt;" in html) == (True, False, True)
