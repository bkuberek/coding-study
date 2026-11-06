"""`GET` and `POST /api/v1/config`: the Settings view's edits of `config.toml`
(docs/specs/web-ui.md#session-and-preferences)."""

import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.toml_config import CONFIG_KEYS
from coding_study.adapters.toml_config_file import TomlConfigFile
from coding_study.domain.config_keys import ConfigKey, KeyKind
from coding_study.entrypoints.commands.serve import workspace_environment
from tests.helpers import SCHEMAS_DIRECTORY, mark_workspace
from tests.web_server import WRITE_HEADERS, session_client, web_app

CONFIG = "/api/v1/config"
KEPT = """\
# keep this comment
[schedule]
max_interval_days = 90 # three months
"""
CHANGED_VALUES: dict[KeyKind, object] = {
    KeyKind.INTEGER: 42,
    KeyKind.CHOICE: "kotlin",
    KeyKind.CHOICES: ["lld"],
}
CHANGED_TEXTS = {
    "progress_db": "other.db",
    "time_limit.value": "3x",
    "study_guides.root": "~/guides",
}


@pytest.fixture
def file(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def app(tmp_path):
    return web_app(tmp_path)


def post(client, changes: dict[str, object], **more: object):
    return client.post(CONFIG, json={"changes": changes, **more}, headers=WRITE_HEADERS)


def by_name(document: dict) -> dict[str, dict]:
    return {key["name"]: key for key in document["keys"]}


def test_the_description_lists_every_key(app):
    with session_client(app) as client:
        document = client.get(CONFIG).json()
    assert [key["name"] for key in document["keys"]] == [key.name for key in CONFIG_KEYS]


def test_the_description_says_where_the_file_is(app, file):
    with session_client(app) as client:
        document = client.get(CONFIG).json()
    assert (document["path"], document["exists"], document["writable"]) == (str(file), False, True)


def test_a_key_shows_its_value_default_type_and_help(app, file):
    file.write_text(KEPT)
    with session_client(app) as client:
        key = by_name(client.get(CONFIG).json())["schedule.max_interval_days"]
    assert (key["value"], key["default"], key["kind"], key["set"]) == (90, 180, "integer", True)


def test_a_key_shows_its_allowed_values(app):
    with session_client(app) as client:
        key = by_name(client.get(CONFIG).json())["default_lang"]
    assert (key["kind"], key["choices"][0], key["applies"] != "") == ("choice", "python", True)


def test_saving_writes_the_changed_key_and_keeps_the_comments(app, file):
    file.write_text(KEPT)
    with session_client(app) as client:
        post(client, {"schedule.max_interval_days": 120})
    assert file.read_text() == KEPT.replace("90", "120")


def test_saving_answers_the_description_and_what_changed(app, file):
    file.write_text(KEPT)
    with session_client(app) as client:
        document = post(client, {"bench.reps": 3, "schedule.max_interval_days": 90}).json()
    assert (document["changed"], by_name(document)["bench.reps"]["value"]) == (["bench.reps"], 3)


def test_saving_creates_a_missing_file(app, file):
    with session_client(app) as client:
        post(client, {"bench.reps": 3})
    assert tomllib.loads(file.read_text()) == {"bench": {"reps": 3}}


def test_a_key_not_in_the_description_gets_422_and_nothing_is_written(app, file):
    file.write_text(KEPT)
    with session_client(app) as client:
        response = post(client, {"schedule.warp_factor": 9})
    assert (response.status_code, response.json()["error"]["code"]) == (422, "usage")
    assert file.read_text() == KEPT


def test_an_invalid_value_gets_422_naming_the_key(app, file):
    with session_client(app) as client:
        response = post(client, {"schedule.ok_first_interval_days": 0})
    assert (response.status_code, response.json()["error"]["message"]) == (
        422,
        "schedule.ok_first_interval_days: expected a positive integer",
    )
    assert not file.exists()


def test_a_body_without_changes_gets_422(app):
    with session_client(app) as client:
        response = client.post(CONFIG, json={}, headers=WRITE_HEADERS)
    assert response.json()["error"]["message"] == "the request needs changes"


def test_changes_that_are_not_an_object_get_422(app):
    with session_client(app) as client:
        response = post(client, ["bench.reps"])  # type: ignore[arg-type]
    assert response.status_code == 422


def test_a_file_that_does_not_parse_still_describes_itself(app, file):
    file.write_text("reps = = 3\n")
    with session_client(app) as client:
        document = client.get(CONFIG).json()
    assert (document["writable"], len(document["issues"])) == (False, 1)


def test_a_file_that_does_not_parse_is_refused_and_kept(app, file):
    file.write_text("reps = = 3\n")
    with session_client(app) as client:
        response = post(client, {"bench.reps": 3})
    assert ("does not parse" in response.json()["error"]["message"], file.read_text()) == (
        True,
        "reps = = 3\n",
    )


@pytest.fixture
def real_environ(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A workspace, and the environment of a server over it with a config of its own."""
    content = tmp_path / "content"
    (content / "problems").mkdir(parents=True)
    (content / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    workspace = Path(mark_workspace(tmp_path / "workspace"))
    config = tmp_path / "config.toml"
    return workspace, {"CSTUDY_CONTENT": str(content), "CSTUDY_CONFIG": str(config)}


def test_a_real_server_s_environment_reads_a_saved_value_on_its_next_call(tmp_path, real_environ):
    workspace, environ = real_environ
    fresh = workspace_environment(workspace, environ, tmp_path)
    before = fresh().config.default_lang
    TomlConfigFile(Path(environ["CSTUDY_CONFIG"])).apply({"default_lang": "go"})
    assert (before.value, fresh().config.default_lang.value) == ("python", "go")


def changed_value(key: ConfigKey) -> object:
    if key.name in CHANGED_TEXTS:
        return CHANGED_TEXTS[key.name]
    if key.kind is KeyKind.BOOLEAN:
        return not key.default
    return CHANGED_VALUES[key.kind]


@pytest.mark.parametrize(
    "key", [key for key in CONFIG_KEYS if not key.reserved], ids=lambda key: key.name
)
def test_each_key_reaches_a_fresh_environment_without_a_restart(tmp_path, real_environ, key):
    """The server builds an Environment per use case call, and each child `cstudy` reads the file
    as it starts, so no key but the watch of `progress_db` waits for a restart."""
    workspace, environ = real_environ
    fresh = workspace_environment(workspace, environ, tmp_path)
    before = fresh().config
    TomlConfigFile(Path(environ["CSTUDY_CONFIG"])).apply({key.name: changed_value(key)})
    assert fresh().config != before
