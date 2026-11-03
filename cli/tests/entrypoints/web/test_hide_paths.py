"""What a Node process cannot open once `hide_paths.cjs` is preloaded
(docs/specs/web-ui.md#hidden-directories): a file of a hidden directory, by every way a language
server might name or open it, while the files around it open as before. `hide_paths_probe.cjs`
opens one hidden file in each of those ways and prints what each did; it runs twice, as a control
without the script, which proves the probe reads where nothing hides, and with it."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.entrypoints.web import language_server
from coding_study.entrypoints.web.language_server import PRELOAD, environment_hiding

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

PROBE = Path(__file__).with_name("hide_paths_probe.cjs")
READ = "READ"
HIDDEN_OUTCOMES = ("ENOENT", "false")
"""What a call that could not open the file ends with: its error code, or what `existsSync`
returns."""
WAYS = [
    "direct",
    "dot-dot",
    "link",
    "dot-dot-after-a-link",
    "relative",
    "url",
    "buffer",
    "open",
    "exists",
    "stat-quiet",
    "readdir",
    "directory",
    "realpath",
    "other-hidden-directory",
    "promise",
    "callback",
    "stream",
    "child",
    "esm",
]
"""The ways that reach a hidden file on every machine."""
SPELLINGS = ["upper-case", "firmlink", "proc-self-root"]
"""Another spelling of the same directory, on the file systems that have one."""


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("hidden") / "ws"
    (root / ".cs" / "build").mkdir(parents=True)
    (root / ".cs" / "build" / "secret.txt").write_text("SECRET\n")
    (root / ".cs" / "cases").mkdir()
    (root / ".cs" / "cases" / "secret.txt").write_text("SECRET\n")
    (root / "typescript" / "practice").mkdir(parents=True)
    (root / "typescript" / "practice" / "fine.txt").write_text("fine\n")
    (root / "python" / ".venv").mkdir(parents=True)
    (root / "projects" / "foo").mkdir(parents=True)
    (root / "projects" / "foo" / ".venv").symlink_to("../../python/.venv", target_is_directory=True)
    (root / "link").symlink_to(".cs/build", target_is_directory=True)
    return root


def probe(workspace: Path, environment: dict[str, str]) -> dict[str, str]:
    done = subprocess.run(
        ["node", str(PROBE), str(workspace)],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(done.stdout)


def hiding(workspace: Path, environment: dict[str, str] | None = None) -> dict[str, str]:
    """The environment a session gives a Node server whose workspace is `workspace`; `.cs/runs`
    is not there yet."""
    hidden = [workspace / ".cs" / "build", workspace / ".cs" / "cases", workspace / ".cs" / "runs"]
    return environment_hiding(environment or dict(os.environ), hidden, [workspace / "typescript"])


@pytest.fixture(scope="module")
def control(workspace) -> dict[str, str]:
    """What each way does where nothing hides the directory."""
    return probe(workspace, dict(os.environ))


@pytest.fixture(scope="module")
def hidden(workspace) -> dict[str, str]:
    return probe(workspace, hiding(workspace))


def test_without_the_script_every_way_reaches_the_file(control):
    assert {way: control[way] for way in WAYS} == dict.fromkeys(WAYS, READ)


@pytest.mark.parametrize("way", WAYS)
def test_with_the_script_no_way_reaches_a_file_of_a_hidden_directory(hidden, way):
    assert hidden[way] in HIDDEN_OUTCOMES


@pytest.mark.parametrize("way", SPELLINGS)
def test_with_the_script_another_spelling_of_the_directory_is_hidden_too(control, hidden, way):
    if control[way] != READ:
        pytest.skip(f"this file system has no {way}")
    assert hidden[way] in HIDDEN_OUTCOMES


def test_the_files_around_a_hidden_directory_still_open(hidden):
    assert hidden["a-file-that-may-be-read"] == READ


def test_a_directory_that_does_not_exist_yet_is_hidden_once_it_does(workspace):
    """`.cs/runs` is made when the first run starts, after the server did."""
    script = (
        "const fs = require('fs'); const path = require('path'); const ws = process.argv[1];"
        "fs.mkdirSync(path.join(ws, '.cs', 'runs'));"
        "fs.writeFileSync(path.join(ws, '.cs', 'runs', 'data.txt'), 'x');"
        "try { fs.readFileSync(path.join(ws, '.cs', 'runs', 'data.txt')); console.log('READ'); }"
        "catch (error) { console.log(error.code); }"
    )
    done = subprocess.run(
        ["node", "-e", script, str(workspace)],
        env=hiding(workspace),
        capture_output=True,
        text=True,
    )
    shutil.rmtree(workspace / ".cs" / "runs", ignore_errors=True)
    assert done.stdout.strip() == "ENOENT"


def test_a_directory_not_there_yet_is_hidden_under_the_names_the_system_will_know_it_by(
    tmp_path, workspace
):
    """It is named through a link, and read by its real path the moment it exists."""
    alias = tmp_path / "alias"
    alias.symlink_to(workspace, target_is_directory=True)
    environment = environment_hiding(
        dict(os.environ), [alias / ".cs" / "later"], [workspace / "typescript"]
    )
    script = (
        "const fs = require('fs'); const path = require('path'); const ws = process.argv[1];"
        "fs.existsSync(path.join(ws, 'typescript'));"  # the script looks for the directory now
        "fs.mkdirSync(path.join(ws, '.cs', 'later'));"
        "fs.writeFileSync(path.join(ws, '.cs', 'later', 'data.txt'), 'x');"
        "try { fs.readFileSync(path.join(ws, '.cs', 'later', 'data.txt')); console.log('READ'); }"
        "catch (error) { console.log(error.code); }"
    )
    done = subprocess.run(
        ["node", "-e", script, str(workspace)], env=environment, capture_output=True, text=True
    )
    shutil.rmtree(workspace / ".cs" / "later", ignore_errors=True)
    assert done.stdout.strip() == "ENOENT"


def test_a_path_with_a_space_and_a_quote_in_it_still_loads_the_script(
    tmp_path, workspace, monkeypatch
):
    copy = tmp_path / 'a b "c"' / "hide_paths.cjs"
    copy.parent.mkdir()
    shutil.copyfile(PRELOAD, copy)
    monkeypatch.setattr(language_server, "PRELOAD", copy)
    assert probe(workspace, hiding(workspace))["direct"] in HIDDEN_OUTCOMES


def test_the_options_the_user_set_for_node_are_kept_beside_the_script(workspace):
    environment = hiding(workspace, {**os.environ, "NODE_OPTIONS": "--max-old-space-size=512"})
    assert probe(workspace, environment)["direct"] in HIDDEN_OUTCOMES
