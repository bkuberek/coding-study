"""The security matrix of docs/specs/web-ui.md#security, one check per test."""

import asyncio
from collections.abc import Iterable
from http.cookies import SimpleCookie

import pytest
from starlette.types import Message, Receive, Scope, Send

from coding_study.entrypoints.web.security import (
    BODY_LIMIT,
    IMPORT_BODY_LIMIT,
    IMPORT_PATH,
    SecurityMiddleware,
    SessionSecrets,
    content_security_policy,
    cookie_name,
    login_url,
)
from tests.web_server import (
    HOST,
    ORIGIN,
    PORT,
    SECRETS,
    WRITE_HEADERS,
    anonymous_client,
    session_client,
    web_app,
)

PREFERENCES = "/api/v1/preferences"
SESSION = "/api/v1/session"
LOCALHOST_ORIGIN = f"http://localhost:{PORT}"
PAGE_POLICY_PARTS = (
    "default-src 'self'",
    "script-src 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
)


@pytest.fixture
def app(tmp_path):
    return web_app(tmp_path)


def error_code(response) -> str:
    return response.json()["error"]["code"]


def session_cookie(response) -> SimpleCookie:
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie


# Session values


def test_the_session_values_are_256_bit_and_distinct():
    secrets = SessionSecrets.generate()
    values = (secrets.token, secrets.cookie, secrets.csrf)
    assert (len(set(values)), {len(value) for value in values}) == (3, {43})


def test_every_start_has_new_session_values():
    assert SessionSecrets.generate() != SessionSecrets.generate()


def test_the_login_url_carries_the_token_on_the_loopback_address():
    assert login_url(PORT, "abc") == f"http://127.0.0.1:{PORT}/?token=abc"


def test_the_cookie_is_named_after_the_port():
    assert cookie_name(PORT) == f"cstudy-{PORT}"


# Host: DNS rebinding


def test_a_request_for_another_host_gets_403_forbidden(app):
    with session_client(app) as client:
        response = client.get(SESSION, headers={"Host": f"rebound.example:{PORT}"})
    assert (response.status_code, error_code(response)) == (403, "forbidden")


def test_the_loopback_address_on_another_port_gets_403(app):
    with session_client(app) as client:
        response = client.get(SESSION, headers={"Host": "127.0.0.1:1"})
    assert response.status_code == 403


def test_localhost_with_the_port_is_an_allowed_host(app):
    with session_client(app) as client:
        response = client.get(SESSION, headers={"Host": f"localhost:{PORT}"})
    assert response.status_code == 200


def test_the_login_checks_the_host_too(app):
    with anonymous_client(app) as client:
        response = client.get(f"/?token={SECRETS.token}", headers={"Host": "rebound.example"})
    assert response.status_code == 403


# Token and cookie


def test_the_token_gets_an_html_page(app):
    with anonymous_client(app) as client:
        response = client.get(f"/?token={SECRETS.token}")
    assert (response.status_code, response.headers["content-type"]) == (
        200,
        "text/html; charset=utf-8",
    )


def test_the_token_page_sends_the_browser_on_to_the_page_without_the_token(app):
    """Not a redirect: a browser withholds a SameSite=Strict cookie set by a redirect that a
    navigation from another site, such as the `--open` file, followed."""
    with anonymous_client(app) as client:
        page = client.get(f"/?token={SECRETS.token}").text
    assert '<meta http-equiv="refresh" content="0; url=/">' in page


def test_the_token_page_is_never_stored(app):
    with anonymous_client(app) as client:
        response = client.get(f"/?token={SECRETS.token}")
    assert response.headers["cache-control"] == "no-store"


def test_the_token_gets_the_session_cookie(app):
    with anonymous_client(app) as client:
        response = client.get(f"/?token={SECRETS.token}")
    assert session_cookie(response)[cookie_name(PORT)].value == SECRETS.cookie


def test_the_session_cookie_is_http_only_same_site_strict_for_the_whole_site(app):
    with anonymous_client(app) as client:
        morsel = session_cookie(client.get(f"/?token={SECRETS.token}"))[cookie_name(PORT)]
    assert (morsel["httponly"], morsel["samesite"].lower(), morsel["path"]) == (
        True,
        "strict",
        "/",
    )


def test_the_session_cookie_has_no_expiry(app):
    with anonymous_client(app) as client:
        morsel = session_cookie(client.get(f"/?token={SECRETS.token}"))[cookie_name(PORT)]
    assert (morsel["expires"], morsel["max-age"]) == ("", "")


def test_the_token_keeps_working(app):
    with anonymous_client(app) as client:
        client.get(f"/?token={SECRETS.token}")
        response = client.get(f"/?token={SECRETS.token}")
    assert session_cookie(response)[cookie_name(PORT)].value == SECRETS.cookie


def test_a_wrong_token_gets_401(app):
    with anonymous_client(app) as client:
        response = client.get("/?token=guessed")
    assert response.status_code == 401


def test_a_wrong_token_gets_no_cookie(app):
    with anonymous_client(app) as client:
        response = client.get("/?token=guessed")
    assert "set-cookie" not in response.headers


def test_the_cookie_opens_the_page(app):
    with anonymous_client(app) as client:
        client.get(f"/?token={SECRETS.token}")
        response = client.get("/")
    assert response.status_code == 200


def test_the_page_without_the_cookie_gets_401_html_naming_the_url_to_open(app):
    with anonymous_client(app) as client:
        response = client.get("/")
    assert (response.status_code, response.headers["content-type"]) == (
        401,
        "text/html; charset=utf-8",
    )


def test_the_401_page_says_to_open_the_url_cstudy_serve_printed(app):
    with anonymous_client(app) as client:
        response = client.get("/")
    assert "open the URL that cstudy serve printed" in response.text


def test_the_api_without_the_cookie_gets_401_unauthorized(app):
    with anonymous_client(app) as client:
        response = client.get(SESSION)
    assert (response.status_code, error_code(response)) == (401, "unauthorized")


def test_a_wrong_cookie_gets_401(app):
    with anonymous_client(app) as client:
        client.cookies.set(cookie_name(PORT), "forged")
        response = client.get(SESSION)
    assert response.status_code == 401


def test_the_cookie_of_another_port_gets_401(app):
    with anonymous_client(app) as client:
        client.cookies.set(cookie_name(PORT + 1), SECRETS.cookie)
        response = client.get(SESSION)
    assert response.status_code == 401


def test_a_cookie_that_is_not_ascii_gets_401(app):
    with anonymous_client(app) as client:
        cookie = f"{cookie_name(PORT)}=café".encode("latin-1")
        response = client.get(SESSION, headers={b"Cookie": cookie})
    assert response.status_code == 401


def test_assets_without_the_cookie_get_401(app):
    with anonymous_client(app) as client:
        response = client.get("/assets/editor.js")
    assert response.status_code == 401


# Origin and CSRF on every write


def test_a_write_from_the_page_passes(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers=WRITE_HEADERS)
    assert response.status_code == 200


def test_a_write_from_the_localhost_origin_passes(app):
    headers = {**WRITE_HEADERS, "Origin": LOCALHOST_ORIGIN}
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers=headers)
    assert response.status_code == 200


def test_a_write_without_an_origin_gets_403_forbidden(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers={"X-Cstudy-CSRF": SECRETS.csrf})
    assert (response.status_code, error_code(response)) == (403, "forbidden")


def test_a_write_from_another_origin_gets_403(app):
    headers = {**WRITE_HEADERS, "Origin": "https://evil.example"}
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers=headers)
    assert response.status_code == 403


def test_a_write_from_the_loopback_address_on_another_port_gets_403(app):
    headers = {**WRITE_HEADERS, "Origin": "http://127.0.0.1:1"}
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers=headers)
    assert response.status_code == 403


def test_a_write_without_the_csrf_header_gets_403_forbidden(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers={"Origin": ORIGIN})
    assert (response.status_code, error_code(response)) == (403, "forbidden")


def test_a_write_with_a_wrong_csrf_header_gets_403(app):
    headers = {**WRITE_HEADERS, "X-Cstudy-CSRF": "guessed"}
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={}, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_every_unsafe_method_needs_the_csrf_header(app, method):
    with session_client(app) as client:
        response = client.request(method, PREFERENCES, headers={"Origin": ORIGIN})
    assert response.status_code == 403


def test_a_refused_write_changes_nothing(app, tmp_path):
    with session_client(app) as client:
        client.put(PREFERENCES, json={"vim": True}, headers={"Origin": ORIGIN})
    assert not (tmp_path / ".cs" / "serve" / "preferences.json").exists()


def test_a_read_needs_no_csrf_header(app):
    with session_client(app) as client:
        response = client.get(PREFERENCES)
    assert response.status_code == 200


# Content Security Policy and response headers


def test_the_page_has_the_strict_policy_with_its_nonce(app):
    with session_client(app) as client:
        response = client.get("/")
    policy = response.headers["content-security-policy"]
    nonce = response.text.split('name="cstudy-csp-nonce" content="')[1].split('"')[0]
    assert policy == content_security_policy(nonce)


def test_the_policy_allows_only_the_pages_own_styles():
    assert content_security_policy("n0nce").split("; ") == [
        *PAGE_POLICY_PARTS[:2],
        "style-src 'self' 'nonce-n0nce'",
        *PAGE_POLICY_PARTS[2:],
    ]


def test_each_page_gets_a_new_nonce(app):
    with session_client(app) as client:
        policies = {client.get("/").headers["content-security-policy"] for _ in range(3)}
    assert len(policies) == 3


def test_other_responses_get_the_policy_without_a_nonce(app):
    with session_client(app) as client:
        response = client.get(SESSION)
    assert response.headers["content-security-policy"] == content_security_policy()


def test_a_refusal_gets_the_policy_too(app):
    with anonymous_client(app) as client:
        response = client.get("/")
    assert response.headers["content-security-policy"] == content_security_policy()


@pytest.mark.parametrize(
    ("header", "value"),
    [
        ("x-content-type-options", "nosniff"),
        ("referrer-policy", "no-referrer"),
        ("cross-origin-resource-policy", "same-origin"),
    ],
)
@pytest.mark.parametrize("path", ["/", SESSION, "/assets/editor.js", "/api/v1/nothing"])
def test_every_response_carries_the_security_headers(app, path, header, value):
    with session_client(app) as client:
        response = client.get(path)
    assert response.headers[header] == value


@pytest.mark.parametrize(
    ("header", "value"),
    [("x-content-type-options", "nosniff"), ("cross-origin-resource-policy", "same-origin")],
)
def test_refusals_carry_the_security_headers(app, header, value):
    with anonymous_client(app) as client:
        response = client.get(SESSION)
    assert response.headers[header] == value


@pytest.mark.parametrize("path", [SESSION, PREFERENCES, "/api/v1/nothing"])
def test_the_api_is_never_cached(app, path):
    with session_client(app) as client:
        response = client.get(path)
    assert response.headers["cache-control"] == "no-store"


def test_the_page_is_never_cached(app):
    with session_client(app) as client:
        response = client.get("/")
    assert response.headers["cache-control"] == "no-store"


# No CORS


def test_no_response_carries_cors_headers(app):
    with session_client(app) as client:
        responses = [
            client.get(SESSION, headers={"Origin": "https://evil.example"}),
            client.put(PREFERENCES, json={}, headers=WRITE_HEADERS),
            client.options(
                PREFERENCES,
                headers={
                    "Origin": "https://evil.example",
                    "Access-Control-Request-Method": "PUT",
                    "Access-Control-Request-Headers": "x-cstudy-csrf",
                },
            ),
        ]
    assert [
        name
        for response in responses
        for name in response.headers
        if name.startswith("access-control-")
    ] == []


def test_a_cross_origin_preflight_fails(app):
    with anonymous_client(app) as client:
        response = client.options(
            PREFERENCES,
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "PUT"},
        )
    assert response.status_code >= 400


# Body size


def test_a_body_over_2_mib_gets_413_too_large(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, content=b" " * (BODY_LIMIT + 1), headers=WRITE_HEADERS)
    assert (response.status_code, error_code(response)) == (413, "too_large")


def test_a_body_of_2_mib_passes_the_limit(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, content=b" " * BODY_LIMIT, headers=WRITE_HEADERS)
    assert response.status_code == 422


def test_a_streamed_body_over_2_mib_gets_413(app):
    chunk = b" " * (1024 * 1024)
    with session_client(app) as client:
        response = client.put(PREFERENCES, content=iter([chunk] * 3), headers=WRITE_HEADERS)
    assert response.status_code == 413


def test_the_limits_are_2_and_64_mib():
    assert (BODY_LIMIT, IMPORT_BODY_LIMIT) == (2 * 1024 * 1024, 64 * 1024 * 1024)


async def body_size(scope: Scope, receive: Receive, send: Send) -> None:
    """An app that answers with the size of the body it read."""
    size = 0
    while True:
        message = await receive()
        size += len(message.get("body", b""))
        if not message.get("more_body"):
            break
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": str(size).encode()})


def write_scope(path: str, *headers: tuple[bytes, bytes]) -> Scope:
    cookie = f"{cookie_name(PORT)}={SECRETS.cookie}".encode()
    return {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (b"host", HOST.encode()),
            (b"cookie", cookie),
            (b"origin", ORIGIN.encode()),
            (b"x-cstudy-csrf", SECRETS.csrf.encode()),
            *headers,
        ],
    }


def post(scope: Scope, chunks: Iterable[bytes]) -> list[Message]:
    """The response messages of the middleware around `body_size`."""
    pending = [{"type": "http.request", "body": chunk, "more_body": True} for chunk in chunks]
    pending.append({"type": "http.request", "body": b"", "more_body": False})
    sent: list[Message] = []

    async def receive() -> Message:
        return pending.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(SecurityMiddleware(body_size, PORT, SECRETS)(scope, receive, send))
    return sent


def status(messages: list[Message]) -> int:
    return messages[0]["status"]


def test_an_import_body_over_2_mib_passes():
    body = post(write_scope(IMPORT_PATH), [b" " * (BODY_LIMIT + 1)])[1]["body"]
    assert body == str(BODY_LIMIT + 1).encode()


def test_an_import_body_declared_over_64_mib_gets_413_unread():
    declared = (b"content-length", str(IMPORT_BODY_LIMIT + 1).encode())
    assert status(post(write_scope(IMPORT_PATH, declared), [])) == 413


def test_an_import_body_streamed_over_64_mib_gets_413():
    mebibyte = b" " * (1024 * 1024)
    assert status(post(write_scope(IMPORT_PATH), [mebibyte] * 65)) == 413


def test_the_import_limit_is_only_for_the_import():
    declared = (b"content-length", str(BODY_LIMIT + 1).encode())
    assert status(post(write_scope("/api/v1/attempts", declared), [])) == 413


# The writes of Settings: the config file and the reset


CONFIG = "/api/v1/config"
RESET = "/api/v1/reset"
SETTINGS_WRITES = (
    (CONFIG, {"changes": {"bench.reps": 3}}),
    (RESET, {"confirm": "reset"}),
)


def written(root) -> bool:
    return (root / "config.toml").exists()


@pytest.mark.parametrize(("path", "body"), SETTINGS_WRITES)
def test_a_settings_write_for_another_host_gets_403(app, tmp_path, path, body):
    with session_client(app) as client:
        response = client.post(
            path, json=body, headers={**WRITE_HEADERS, "Host": f"rebound.example:{PORT}"}
        )
    assert (response.status_code, error_code(response), written(tmp_path)) == (
        403,
        "forbidden",
        False,
    )


@pytest.mark.parametrize(("path", "body"), SETTINGS_WRITES)
def test_a_settings_write_from_another_origin_gets_403(app, tmp_path, path, body):
    with session_client(app) as client:
        response = client.post(
            path, json=body, headers={**WRITE_HEADERS, "Origin": "http://evil.example"}
        )
    assert (response.status_code, error_code(response), written(tmp_path)) == (
        403,
        "forbidden",
        False,
    )


@pytest.mark.parametrize(("path", "body"), SETTINGS_WRITES)
def test_a_settings_write_without_the_cookie_gets_401(app, tmp_path, path, body):
    with anonymous_client(app) as client:
        response = client.post(path, json=body, headers=WRITE_HEADERS)
    assert (response.status_code, error_code(response), written(tmp_path)) == (
        401,
        "unauthorized",
        False,
    )


@pytest.mark.parametrize(("path", "body"), SETTINGS_WRITES)
def test_a_settings_write_without_the_csrf_token_gets_403(app, tmp_path, path, body):
    with session_client(app) as client:
        response = client.post(path, json=body, headers={"Origin": ORIGIN})
    assert (response.status_code, error_code(response), written(tmp_path)) == (
        403,
        "forbidden",
        False,
    )


# The writes of the sets


SET_FILE = "sets:\n  backend-loop:\n    problems:\n      - two-sum\n"
SET_WRITES = (
    ("POST", "/api/v1/sets", {"name": "other"}),
    ("POST", "/api/v1/sets/backend-loop/add", {"slugs": ["lru-cache"]}),
    ("POST", "/api/v1/sets/backend-loop/remove", {"slugs": ["two-sum"]}),
    ("POST", "/api/v1/sets/backend-loop/move", {"slug": "two-sum", "position": 1}),
    ("POST", "/api/v1/sets/backend-loop/rename", {"to": "other"}),
    ("DELETE", "/api/v1/sets/backend-loop", {"confirm": True}),
)


@pytest.fixture
def sets_file(tmp_path):
    file = tmp_path / "sets.yaml"
    file.write_text(SET_FILE)
    return file


@pytest.mark.parametrize(("method", "path", "body"), SET_WRITES)
def test_a_set_write_for_another_host_gets_403(app, sets_file, method, path, body):
    with session_client(app) as client:
        response = client.request(
            method, path, json=body, headers={**WRITE_HEADERS, "Host": f"rebound.example:{PORT}"}
        )
    assert (response.status_code, error_code(response), sets_file.read_text()) == (
        403,
        "forbidden",
        SET_FILE,
    )


@pytest.mark.parametrize(("method", "path", "body"), SET_WRITES)
def test_a_set_write_from_another_origin_gets_403(app, sets_file, method, path, body):
    with session_client(app) as client:
        response = client.request(
            method, path, json=body, headers={**WRITE_HEADERS, "Origin": "http://evil.example"}
        )
    assert (response.status_code, error_code(response), sets_file.read_text()) == (
        403,
        "forbidden",
        SET_FILE,
    )


@pytest.mark.parametrize(("method", "path", "body"), SET_WRITES)
def test_a_set_write_without_the_cookie_gets_401(app, sets_file, method, path, body):
    with anonymous_client(app) as client:
        response = client.request(method, path, json=body, headers=WRITE_HEADERS)
    assert (response.status_code, error_code(response), sets_file.read_text()) == (
        401,
        "unauthorized",
        SET_FILE,
    )


@pytest.mark.parametrize(("method", "path", "body"), SET_WRITES)
def test_a_set_write_without_the_csrf_token_gets_403(app, sets_file, method, path, body):
    with session_client(app) as client:
        response = client.request(method, path, json=body, headers={"Origin": ORIGIN})
    assert (response.status_code, error_code(response), sets_file.read_text()) == (
        403,
        "forbidden",
        SET_FILE,
    )
