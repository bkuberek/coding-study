"""The web UI's app on a test workspace, and HTTP clients for it (docs/specs/web-ui.md)."""

import hashlib
import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from starlette.testclient import TestClient
from starlette.types import ASGIApp

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.environment import Environment
from coding_study.entrypoints.web.app import create_app
from coding_study.entrypoints.web.context import ServerSettings
from coding_study.entrypoints.web.security import SessionSecrets, cookie_name
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY

PORT = 53817
HOST = f"127.0.0.1:{PORT}"
ORIGIN = f"http://{HOST}"
SECRETS = SessionSecrets(token="the-token", cookie="the-cookie", csrf="the-csrf")
WRITE_HEADERS = {"Origin": ORIGIN, "X-Cstudy-CSRF": SECRETS.csrf}
TEST_VERSION = "9.9.9"
ENTRY = "editor.js"
HASHED_CHUNK = "chunks/go-6P5FBZMG.js"
UNLISTED = "notes.txt"
ASSETS = {ENTRY: "export {};\n", HASHED_CHUNK: "export const go = 1;\n"}


def static_directory(root: Path) -> Path:
    """A built front end: an entry module and a content-hashed chunk, which its manifest lists,
    and a file it does not list."""
    static = root / "static"
    for path, text in {**ASSETS, UNLISTED: "not built\n"}.items():
        (static / path).parent.mkdir(parents=True, exist_ok=True)
        (static / path).write_text(text)
    digests = {path: hashlib.sha256(text.encode()).hexdigest() for path, text in ASSETS.items()}
    (static / "manifest.json").write_text(json.dumps({"entry": ENTRY, "files": digests}))
    return static


def web_workspace(root: Path, **overrides: object) -> Environment:
    """A workspace that is its own content root, holding the real schemas."""
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas", dirs_exist_ok=True)
    return make_environment(root, **overrides)


def web_app(root: Path, environment: Environment | None = None) -> ASGIApp:
    """The app of a server on `PORT` over the workspace `root`."""
    workspace = environment or web_workspace(root)
    return create_app(
        ServerSettings(
            port=PORT,
            version=TEST_VERSION,
            secrets=SECRETS,
            static_directory=static_directory(root),
            load_environment=lambda: workspace,
            preferences=FsPreferencesStore(root),
        )
    )


@contextmanager
def anonymous_client(app: ASGIApp) -> Iterator[TestClient]:
    """A browser tab on the server's address that has not logged in."""
    with TestClient(
        app, base_url=ORIGIN, follow_redirects=False, raise_server_exceptions=False
    ) as client:
        yield client


@contextmanager
def session_client(app: ASGIApp) -> Iterator[TestClient]:
    """A browser tab holding the session cookie."""
    with anonymous_client(app) as client:
        client.cookies.set(cookie_name(PORT), SECRETS.cookie)
        yield client
