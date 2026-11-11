"""`/api/v1/guides` and `/api/v1/paths` (docs/specs/web-ui.md#guides): the documents of
`cstudy learn --json`, a guide's HTML with its diagrams ready to draw, marking a guide read as
`cstudy learn <guide> --done` does, and a problem's `guides`."""

import html
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.domain.guide_markdown import mermaid_digest
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import learn
from tests.fakes import NOW, make_environment
from tests.guide_builders import DIAGRAM, write_guide, write_hashing
from tests.web_server import WRITE_HEADERS, session_client, web_app

GUIDES = "/api/v1/guides"
PATHS = "/api/v1/paths"
LINKED = """# Linked

## The idea

Read [hash functions](../hash-functions/guide.md) first, then [the docs](https://docs.python.org/3/).
A [file](examples/hello.py) is no page.

```python
seen = {}
```
"""
runner = CliRunner()


@pytest.fixture
def environment(content_root: Path) -> Environment:
    write_hashing(content_root)
    meta = content_root / "problems" / "0001-two-sum" / "meta.yaml"
    meta.write_text(f"{meta.read_text()}guides: [hash-maps, hash-functions]\n")
    return make_environment(content_root)


@pytest.fixture
def client(tmp_path: Path, environment: Environment):
    with session_client(web_app(tmp_path / "server", environment)) as opened:
        yield opened


def cli_document(monkeypatch: pytest.MonkeyPatch, environment: Environment, *arguments: str):
    monkeypatch.setattr(learn, "load_environment", lambda *_: environment)
    monkeypatch.setattr(learn, "load_catalog_environment", lambda *_: environment)
    return json.loads(runner.invoke(cli.app, ["learn", *arguments, "--json"]).stdout)


def mark(client, slug: str):
    return client.post(f"{GUIDES}/{slug}/read", json={}, headers=WRITE_HEADERS)


def error(response) -> tuple[int, str, str]:
    body = response.json()["error"]
    return response.status_code, body["code"], body["message"]


def test_the_list_is_the_document_of_cstudy_learn(client, monkeypatch, environment):
    mark(client, "hash-functions")
    assert client.get(GUIDES).json() == cli_document(monkeypatch, environment)


def test_a_guide_is_the_document_of_cstudy_learn_with_its_html(client, monkeypatch, environment):
    document = client.get(f"{GUIDES}/hash-maps").json()
    html = document.pop("html")
    assert (document, html.startswith("<")) == (
        cli_document(monkeypatch, environment, "hash-maps"),
        True,
    )


def test_a_diagram_carries_its_source_and_hides_its_text_drawing(client):
    page = client.get(f"{GUIDES}/hash-maps").json()["html"]
    assert (
        f'<figure class="diagram" data-mermaid="{html.escape(DIAGRAM)}">' in page,
        '<pre class="diagram-text" hidden><code>[k] --&gt; [b]\n</code></pre>' in page,
        "text-of-mermaid" in page,
        mermaid_digest(DIAGRAM) in page,
        "language-mermaid" in page,
    ) == (True, True, False, False, False)


def test_a_guide_leaves_out_its_title_heading_which_the_view_shows(client):
    html = client.get(f"{GUIDES}/hash-maps").json()["html"]
    assert ("<h1>" in html, html.startswith("<h2>The idea</h2>")) == (False, True)


def test_a_guide_highlights_its_code_and_links_to_other_guides(content_root, client):
    write_guide(content_root, "linked", "Linked", markdown=LINKED)
    html = client.get(f"{GUIDES}/linked").json()["html"]
    assert (
        '<a href="#/guides/hash-functions">hash functions</a>' in html,
        'href="https://docs.python.org/3/"' in html,
        "A file is no page." in html,
        '<span class="tok-n">seen</span>' in html,
    ) == (True, True, True, True)


def test_a_path_is_the_document_of_cstudy_learn_path(client, monkeypatch, environment):
    mark(client, "hash-functions")
    assert client.get(f"{PATHS}/hashing").json() == cli_document(
        monkeypatch, environment, "--path", "hashing"
    )


def test_marking_a_guide_read_answers_as_done_does(client, monkeypatch, environment):
    first = mark(client, "hash-maps")
    assert (first.status_code, first.json(), mark(client, "hash-maps").json()["already"]) == (
        200,
        {"slug": "hash-maps", "read_at": NOW.isoformat(), "already": False},
        True,
    )


def test_a_guide_marked_read_counts_in_the_path_as_in_the_terminal(
    client, monkeypatch, environment
):
    mark(client, "hash-maps")
    terminal = cli_document(monkeypatch, environment, "--path", "hashing")
    page = client.get(f"{PATHS}/hashing").json()
    assert (page["done"], page["steps"][1]["status"], page) == (1, "read", terminal)


def test_marking_needs_the_csrf_header(client):
    response = client.post(f"{GUIDES}/hash-maps/read", json={})
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (f"{GUIDES}/hash-map", 'unknown guide "hash-map"; did you mean hash-maps?'),
        (f"{PATHS}/hashin", 'unknown path "hashin"; did you mean hashing?'),
    ],
)
def test_an_unknown_guide_or_path_is_not_found_with_the_clis_message(client, path, message):
    assert error(client.get(path)) == (404, "not_found", message)


def test_marking_an_unknown_guide_is_not_found(client):
    assert error(mark(client, "nope"))[:2] == (404, "not_found")


def test_a_problem_names_its_guides_with_their_titles_and_read_state(client):
    mark(client, "hash-functions")
    assert client.get("/api/v1/problems/two-sum").json()["guides"] == [
        {"slug": "hash-maps", "title": "Hash maps", "read": False},
        {"slug": "hash-functions", "title": "Hash functions", "read": True},
    ]


def test_a_problem_without_guides_has_none(client):
    assert client.get("/api/v1/problems/lru-cache").json()["guides"] == []
