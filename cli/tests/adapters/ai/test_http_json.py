"""The HTTP rules of docs/specs/ai.md#http and #errors, over `tests/fake_ai_provider.py` on the
loopback."""

import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from coding_study.adapters.ai.http_json import (
    ENDPOINT_VARIABLE,
    MAX_REPLY_BYTES,
    JsonClient,
    endpoint_override,
)
from coding_study.adapters.ai.models import ProviderModels
from coding_study.adapters.environment_factory import NoLanguageModels
from coding_study.domain.ai import AI_OFF, ApiKey, ModelRef, Provider
from coding_study.domain.ai_models import ModelRequest, ProviderError, ProviderErrorKind
from coding_study.domain.errors import ConfigError, UsageError
from tests.fake_ai_provider import Answer, FakeAiProvider, Route

SECRET = "sk-secret-0123456789"
KEY = ApiKey(SECRET)
ORIGIN = "https://api.anthropic.com"
PATH = "/v1/messages"
HEADERS = {"x-api-key": SECRET, "anthropic-version": "2023-06-01"}
BODY = {"model": "m", "messages": []}


@pytest.fixture
def provider() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as fake:
        yield fake


@pytest.fixture
def client(provider: FakeAiProvider) -> JsonClient:
    return JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1.2.3")


def post(client: JsonClient, deadline_s: float = 5.0, model_id: str | None = None):
    return client.post(
        Provider.ANTHROPIC,
        ORIGIN,
        PATH,
        BODY,
        headers=HEADERS,
        key=KEY,
        deadline_s=deadline_s,
        model_id=model_id,
    )


def script(provider: FakeAiProvider, *answers: Answer) -> None:
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, *answers)


def failure(client: JsonClient, **keywords) -> ProviderError:
    with pytest.raises(ProviderError) as raised:
        post(client, **keywords)
    assert SECRET not in str(raised.value)
    return raised.value


def test_a_post_sends_the_body_to_the_providers_path_and_returns_the_reply(provider, client):
    script(provider, Answer(json={"content": [{"text": "ok"}]}))
    assert post(client) == {"content": [{"text": "ok"}]}
    (received,) = provider.received
    assert (received.method, received.path) == ("POST", PATH)
    assert received.json == BODY


def test_a_get_returns_the_reply(provider, client):
    provider.script(Provider.ANTHROPIC, Route.MODELS, Answer(json={"data": []}))
    reply = client.get(
        Provider.ANTHROPIC, ORIGIN, "/v1/models", headers=HEADERS, key=KEY, deadline_s=5
    )
    assert reply == {"data": []}
    assert provider.received[0].method == "GET"


def test_the_headers_are_the_keys_the_version_and_the_agent(provider, client):
    script(provider, Answer(json={}))
    post(client)
    headers = provider.received[0].headers
    assert headers["content-type"] == "application/json"
    assert headers["x-api-key"] == SECRET
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["user-agent"] == "cstudy/1.2.3"
    assert set(headers) == {
        "content-type",
        "x-api-key",
        "anthropic-version",
        "user-agent",
        "host",
        "content-length",
        "accept-encoding",
        "connection",
    }


def test_a_get_sends_no_content_type(provider, client):
    provider.script(Provider.ANTHROPIC, Route.MODELS, Answer(json={}))
    client.get(Provider.ANTHROPIC, ORIGIN, "/v1/models", headers={}, key=KEY, deadline_s=5)
    assert "content-type" not in provider.received[0].headers


def test_a_request_is_sent_once_and_never_retried(provider, client):
    script(provider, Answer(503, json={"error": {"message": "busy"}}), Answer(json={}))
    assert failure(client).kind is ProviderErrorKind.PROVIDER
    assert len(provider.received) == 1


@pytest.mark.parametrize(
    ("status", "kind", "message"),
    [
        (
            401,
            ProviderErrorKind.AUTH,
            "anthropic refused the key (401): set it again with cstudy ai key anthropic",
        ),
        (
            403,
            ProviderErrorKind.AUTH,
            "anthropic refused the key (403): set it again with cstudy ai key anthropic",
        ),
        (
            429,
            ProviderErrorKind.RATE_LIMIT,
            "anthropic is limiting this key's requests (429): try again later",
        ),
        (
            404,
            ProviderErrorKind.MODEL,
            "anthropic has no model claude-x, or it cannot answer in a JSON schema: "
            "see cstudy ai models anthropic",
        ),
    ],
)
def test_a_status_maps_to_its_kind_and_message(provider, client, status, kind, message):
    script(provider, Answer(status, json={"error": {"message": "nope"}}))
    error = failure(client, model_id="claude-x")
    assert (error.kind, str(error)) == (kind, message)


def test_a_404_without_a_model_is_a_provider_failure(provider, client):
    script(provider, Answer(404, json={"error": {"message": "gone"}}))
    error = failure(client)
    assert (error.kind, str(error)) == (ProviderErrorKind.PROVIDER, "anthropic failed (404): gone")


@pytest.mark.parametrize(
    "message",
    ["The model `claude-x` does not exist", "output_config.format: invalid schema"],
)
def test_a_400_that_names_the_model_or_the_schema_is_a_model_error(provider, client, message):
    script(provider, Answer(400, json={"error": {"message": message}}))
    assert failure(client, model_id="claude-x").kind is ProviderErrorKind.MODEL


def test_any_other_400_is_a_provider_failure(provider, client):
    script(provider, Answer(400, json={"error": {"message": "max_tokens is too large"}}))
    error = failure(client, model_id="claude-x")
    assert error.kind is ProviderErrorKind.PROVIDER
    assert str(error) == "anthropic failed (400): max_tokens is too large"


def test_a_5xx_carries_the_first_200_characters_of_the_providers_message(provider, client):
    script(provider, Answer(502, json={"error": {"message": "x" * 500}}))
    assert str(failure(client)) == f"anthropic failed (502): {'x' * 200}"


@pytest.mark.parametrize(
    ("answer", "shown"),
    [
        (Answer(500, json={"error": "flat"}), "flat"),
        (Answer(500, json={"message": "top"}), "top"),
        (Answer(500, body=b"not  json\n at all"), "not json at all"),
        (Answer(500, json=[1, 2]), "[1, 2]"),
    ],
)
def test_the_message_is_found_where_providers_put_it(provider, client, answer, shown):
    script(provider, answer)
    assert str(failure(client)) == f"anthropic failed (500): {shown}"


def test_a_redirect_is_a_failure_and_the_key_is_not_sent_on(provider, client):
    script(provider, Answer(302, headers={"Location": "http://127.0.0.1:9/elsewhere"}))
    error = failure(client)
    assert str(error).startswith("anthropic failed (302)")
    assert len(provider.received) == 1


def test_the_key_is_replaced_in_a_providers_message(provider, client):
    script(provider, Answer(500, json={"error": {"message": f"bad key {SECRET} in header"}}))
    error = failure(client)
    assert str(error) == "anthropic failed (500): bad key <key> in header"


def test_the_key_is_replaced_even_where_truncation_would_cut_it(provider, client):
    message = "y" * 190 + SECRET
    script(provider, Answer(500, json={"error": {"message": message}}))
    assert str(failure(client)) == f"anthropic failed (500): {'y' * 190}<key>"


def test_a_reply_that_is_not_a_json_object_is_invalid(provider, client):
    script(provider, Answer(body=b"<html>"), Answer(json=[1]))
    assert failure(client).kind is ProviderErrorKind.INVALID_REPLY
    assert failure(client).kind is ProviderErrorKind.INVALID_REPLY


def test_a_reply_over_4_mib_is_refused_as_invalid(provider, client):
    script(provider, Answer(body=b" " * (MAX_REPLY_BYTES + 1)))
    error = failure(client)
    assert error.kind is ProviderErrorKind.INVALID_REPLY
    assert str(error) == "anthropic sent a reply over 4 MiB"


def test_a_reply_of_4_mib_is_read(provider, client):
    padding = b" " * (MAX_REPLY_BYTES - 2)
    script(provider, Answer(body=b"{}" + padding))
    assert post(client) == {}


def test_a_reply_that_grows_past_4_mib_without_saying_so_is_refused(provider, client):
    """No Content-Length would show the size ahead: the chunked reply is counted as it comes."""

    class Chunked(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            piece = b"x" * 65536
            try:
                for _ in range(MAX_REPLY_BYTES // len(piece) + 2):
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(piece), piece))
                self.wfile.write(b"0\r\n\r\n")
            except OSError:
                return

        def log_message(self, format, *arguments):
            return

    server = HTTPServer(("127.0.0.1", 0), Chunked)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_address[1]}"
        error = failure(JsonClient({ENDPOINT_VARIABLE: endpoint}, "1"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert error.kind is ProviderErrorKind.INVALID_REPLY


def test_a_request_past_its_deadline_times_out(provider, client):
    script(provider, Answer(json={}, delay_s=2))
    error = failure(client, deadline_s=0.3)
    assert (error.kind, str(error)) == (
        ProviderErrorKind.TIMEOUT,
        "anthropic did not answer within 0.3 s",
    )


def test_the_deadline_covers_the_whole_request_not_each_read(provider, client):
    """A reply that keeps coming, a few bytes at a time, still stops at the deadline."""
    script(provider, Answer(json={"text": "z" * 400}, drip_s=0.1))
    assert failure(client, deadline_s=0.5).kind is ProviderErrorKind.TIMEOUT


def test_a_slow_reply_within_its_deadline_is_read_whole(provider, client):
    script(provider, Answer(json={"ok": True}, delay_s=0.4))
    assert post(client, deadline_s=5) == {"ok": True}


def test_a_connection_that_is_refused_is_a_network_error(client):
    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
    unreachable = JsonClient({ENDPOINT_VARIABLE: f"http://127.0.0.1:{port}"}, "1")
    error = failure(unreachable)
    assert error.kind is ProviderErrorKind.NETWORK
    assert str(error) == "could not reach 127.0.0.1: Connection refused"


def test_a_server_that_hangs_up_is_a_network_error(client):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()

    def hang_up() -> None:
        connection, _ = listener.accept()
        connection.recv(65536)
        connection.close()

    thread = threading.Thread(target=hang_up, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{listener.getsockname()[1]}"
        error = failure(JsonClient({ENDPOINT_VARIABLE: endpoint}, "1"))
    finally:
        thread.join()
        listener.close()
    assert error.kind is ProviderErrorKind.NETWORK
    assert str(error).startswith("could not reach 127.0.0.1: ")


def test_a_proxy_is_used_for_a_provider_and_never_for_the_test_endpoint(provider, monkeypatch):
    """`HTTPS_PROXY` is read as urllib reads it: the tunnel request goes to the proxy, which here
    is a loopback server that refuses it, so the provider's host is never looked up."""
    refusals: list[str] = []

    class Proxy(BaseHTTPRequestHandler):
        def do_CONNECT(self):
            refusals.append(self.path)
            self.send_error(502, "no tunnel")

        def log_message(self, format, *arguments):
            return

    server = HTTPServer(("127.0.0.1", 0), Proxy)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    try:
        via_proxy = failure(JsonClient({}, "1"))
        script(provider, Answer(json={"ok": 1}))
        direct = post(JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert refusals == ["api.anthropic.com:443"]
    assert via_proxy.kind is ProviderErrorKind.NETWORK
    assert str(via_proxy).startswith("could not reach api.anthropic.com: ")
    assert direct == {"ok": 1}


def test_the_tls_context_checks_certificates_and_hostnames():
    context = JsonClient({}, "1")._tls()
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.check_hostname


@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
def test_both_loopback_addresses_are_accepted(host):
    with FakeAiProvider(host) as fake:
        script(fake, Answer(json={"host": host}))
        assert post(JsonClient({ENDPOINT_VARIABLE: fake.endpoint}, "1")) == {"host": host}


@pytest.mark.parametrize(
    ("value", "origin"),
    [
        ("http://127.0.0.1:8080", "http://127.0.0.1:8080"),
        ("http://127.0.0.1:8080/", "http://127.0.0.1:8080"),
        ("http://[::1]:9000", "http://[::1]:9000"),
    ],
)
def test_the_endpoint_is_a_loopback_url_and_a_port(value, origin):
    assert endpoint_override({ENDPOINT_VARIABLE: value}) == origin


def test_no_endpoint_is_no_override():
    assert endpoint_override({}) is None


@pytest.mark.parametrize(
    "value",
    [
        "",
        "http://localhost:8080",
        "http://127.0.0.2:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:99999",
        "http://127.0.0.1:abc",
        "https://127.0.0.1:8080",
        "http://[::2]:8080",
        "http://api.anthropic.com:80",
        "http://user@127.0.0.1:8080",
        "http://127.0.0.1:8080@example.com:80",
        "http://127.0.0.1:8080/v1",
        "http://127.0.0.1:8080?x=1",
        "http://127.0.0.1:8080#x",
        "127.0.0.1:8080",
        "ftp://127.0.0.1:8080",
    ],
)
def test_any_other_endpoint_is_refused_as_a_config_error(value):
    with pytest.raises(ConfigError) as raised:
        JsonClient({ENDPOINT_VARIABLE: value}, "1")
    assert str(raised.value).startswith("CSTUDY_AI_ENDPOINT: expected http://127.0.0.1:<port> or ")


def test_a_refused_endpoint_sends_nothing_even_to_the_loopback(provider):
    environ = {ENDPOINT_VARIABLE: provider.endpoint.replace("127.0.0.1", "localhost")}
    with pytest.raises(ConfigError):
        JsonClient(environ, "1")
    assert provider.received == []


def request(model: str = "anthropic:m") -> ModelRequest:
    return ModelRequest(ModelRef.parse(model), "be brief", "hello", 100, 5.0)


def test_a_provider_without_an_adapter_is_an_error_naming_it(client):
    models = ProviderModels(client, {})
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert str(raised.value) == "this cstudy has no adapter for anthropic"
    with pytest.raises(ProviderError):
        models.list_models(Provider.GOOGLE, KEY, 5.0)


def test_the_port_hands_each_request_to_its_providers_adapter_once_opened(client):
    class Adapter:
        def __init__(self, client: JsonClient) -> None:
            self.client = client

        def complete(self, request, key):
            return request.model.model_id

        def list_models(self, key, deadline_s):
            return ("a", "b")

    opened: list[Provider] = []

    def factory(provider: Provider):
        def make(client: JsonClient) -> Adapter:
            opened.append(provider)
            return Adapter(client)

        return make

    models = ProviderModels(
        client,
        {
            Provider.ANTHROPIC: factory(Provider.ANTHROPIC),
            Provider.OPENAI: factory(Provider.OPENAI),
        },
    )
    assert models.complete(request("anthropic:one"), KEY) == "one"
    assert models.complete(request("anthropic:two"), KEY) == "two"
    assert models.list_models(Provider.OPENAI, KEY, 5.0) == ("a", "b")
    assert opened == [Provider.ANTHROPIC, Provider.OPENAI]


def test_no_language_models_refuses_every_request():
    models = NoLanguageModels()
    with pytest.raises(UsageError) as complete:
        models.complete(request(), KEY)
    with pytest.raises(UsageError) as listing:
        models.list_models(Provider.OPENAI, KEY, 5.0)
    assert str(complete.value) == str(listing.value) == AI_OFF
    assert AI_OFF.startswith("AI is off: turn it on with ai.enabled = true")
