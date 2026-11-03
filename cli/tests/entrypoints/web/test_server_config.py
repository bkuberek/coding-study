"""How `cstudy serve` starts uvicorn (docs/specs/web-ui.md#process): the one WebSocket route runs on
wsproto, whatever other WebSocket library is installed, without compression and with messages of
at most 4 MiB."""

from uvicorn.protocols.websockets.wsproto_impl import WSProtocol

from coding_study.entrypoints.web.server import uvicorn_config
from tests.web_server import web_app

MIB = 1024 * 1024


def loaded(tmp_path):
    config = uvicorn_config(web_app(tmp_path))
    config.load()
    return config


def test_websockets_run_on_wsproto(tmp_path):
    config = loaded(tmp_path)
    assert (config.ws, config.ws_protocol_class) == ("wsproto", WSProtocol)


def test_a_message_is_at_most_4_mib(tmp_path):
    assert loaded(tmp_path).ws_max_size == 4 * MIB


def test_messages_are_not_compressed(tmp_path):
    assert loaded(tmp_path).ws_per_message_deflate is False


def test_http_is_still_h11_and_the_lifespan_is_on(tmp_path):
    config = loaded(tmp_path)
    assert (config.http, config.lifespan) == ("h11", "on")
