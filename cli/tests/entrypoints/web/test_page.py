"""`GET /` and `GET /assets/{file}` (docs/specs/web-ui.md#session-and-preferences)."""

import pytest

from tests.web_server import ENTRY, HASHED_CHUNK, SECRETS, UNLISTED, session_client, web_app


@pytest.fixture
def app(tmp_path):
    return web_app(tmp_path)


def meta(page: str, name: str) -> str:
    return page.split(f'<meta name="{name}" content="')[1].split('"')[0]


def test_the_page_embeds_the_csrf_token(app):
    with session_client(app) as client:
        page = client.get("/").text
    assert meta(page, "cstudy-csrf") == SECRETS.csrf


def test_the_page_embeds_the_nonce_of_its_policy(app):
    with session_client(app) as client:
        response = client.get("/")
    nonce = meta(response.text, "cstudy-csp-nonce")
    assert f"'nonce-{nonce}'" in response.headers["content-security-policy"]


def test_the_nonce_is_128_bits(app):
    with session_client(app) as client:
        assert len(meta(client.get("/").text, "cstudy-csp-nonce")) == 22


def test_the_page_is_html(app):
    with session_client(app) as client:
        response = client.get("/")
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_an_asset_is_served(app):
    with session_client(app) as client:
        response = client.get(f"/assets/{ENTRY}")
    assert (response.status_code, response.text) == (200, "export {};\n")


def test_a_content_hashed_asset_is_cached_for_a_year(app):
    with session_client(app) as client:
        response = client.get(f"/assets/{HASHED_CHUNK}")
    assert response.headers["cache-control"] == "max-age=31536000, immutable"


def test_an_asset_without_a_hash_is_revalidated(app):
    with session_client(app) as client:
        response = client.get(f"/assets/{ENTRY}")
    assert response.headers["cache-control"] == "no-cache"


def test_a_missing_asset_gets_404_not_found(app):
    with session_client(app) as client:
        response = client.get("/assets/missing.js")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")


@pytest.mark.parametrize("path", [UNLISTED, "manifest.json", "chunks", "../web_server.py"])
def test_only_the_files_the_manifest_lists_are_served(app, path):
    with session_client(app) as client:
        response = client.get(f"/assets/{path}")
    assert response.status_code == 404


def test_an_asset_is_served_with_its_type(app):
    with session_client(app) as client:
        response = client.get(f"/assets/{HASHED_CHUNK}")
    assert response.headers["content-type"] == "text/javascript; charset=utf-8"


def test_the_page_names_the_editors_nonce_option(app):
    """The page's code passes the nonce to `createEditor({nonce})` of the editor module."""
    with session_client(app) as client:
        page = client.get("/").text
    assert "createEditor({nonce})" in page


def test_the_page_carries_its_icon_inline_as_its_policy_allows(app):
    """An inline icon spares browsers a request for `/favicon.ico`, which would get 404."""
    with session_client(app) as client:
        response = client.get("/")
    assert '<link rel="icon" href="data:image/svg+xml,' in response.text
    assert "img-src 'self' data:" in response.headers["content-security-policy"]


def test_only_the_root_serves_the_page(app):
    with session_client(app) as client:
        response = client.get("/problems")
    assert response.status_code == 404
