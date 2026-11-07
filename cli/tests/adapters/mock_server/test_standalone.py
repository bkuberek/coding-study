"""The program as it runs in its container: this folder alone, on the standard library alone.

`-S` keeps the venv's site-packages off the path, as a Python image has no cstudy to find there.
"""

import ast
import json
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest

import coding_study.adapters.mock_server as mock_server
from coding_study.adapters.mock_server.http_server import ListenOn
from coding_study.adapters.mock_server.program import parse_options
from tests.mock_server_support import (
    GENEROUS_WAIT_S,
    SAMPLE_CONFIG,
    StackClient,
    sample_document,
    with_held_scenarios,
    write_config,
)

SERVER_FOLDER = Path(mock_server.__file__).parent
SERVER_FILES = sorted(SERVER_FOLDER.glob("*.py"))
AVAILABILITY = "/v1/rooms/availability?date=2027-03-01"
READ_ONLY = 0o555
WRITABLE = 0o755
EXIT_CLEAN = 0


def copied_alone(folder: Path, name: str = "mock_server") -> Path:
    target = folder / name
    shutil.copytree(SERVER_FOLDER, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def command(server: Path, *arguments: str) -> list[str]:
    return [sys.executable, "-I", "-S", str(server), *arguments]


def on_any_port(server: Path, config: Path) -> list[str]:
    ports = ("--bind", "127.0.0.1", "--api-port", "0", "--control-port", "0")
    return command(server, str(config), *ports)


@contextmanager
def running(server: Path, config: Path) -> Iterator[tuple[subprocess.Popen[str], dict]]:
    """The process and the document it printed once it was listening."""
    process = subprocess.Popen(
        on_any_port(server, config),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as reader:
            line = reader.submit(process.stdout.readline).result(timeout=GENEROUS_WAIT_S)
        yield process, json.loads(line)
    finally:
        process.kill()
        process.communicate(timeout=GENEROUS_WAIT_S)


def client_of(started: dict) -> StackClient:
    return StackClient(started["api_port"], started["control_port"])


def imported_modules(path: Path) -> list[tuple[str, int]]:
    """Each import of a file: the module's top-level name, and how many dots it was relative by."""
    tree = ast.parse(path.read_text())
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [(alias.name.split(".")[0], 0) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules.append(((node.module or "").split(".")[0], node.level))
    return modules


@pytest.mark.parametrize("path", SERVER_FILES, ids=lambda path: path.name)
def test_a_server_file_imports_only_its_siblings_and_the_standard_library(path: Path):
    outsiders = [
        name
        for name, level in imported_modules(path)
        if level != 1 and (level > 1 or name not in sys.stdlib_module_names)
    ]
    assert outsiders == []


def test_a_copy_of_the_folder_alone_serves(tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (_, started):
        assert client_of(started).api(AVAILABILITY).status == 200


def test_the_folder_may_have_any_name(tmp_path: Path):
    with running(copied_alone(tmp_path, "renamed"), SAMPLE_CONFIG) as (_, started):
        assert client_of(started).api(AVAILABILITY).status == 200


def test_a_read_only_folder_serves(tmp_path: Path):
    server = copied_alone(tmp_path)
    server.chmod(READ_ONLY)
    try:
        with running(server, SAMPLE_CONFIG) as (_, started):
            assert client_of(started).api(AVAILABILITY).status == 200
    finally:
        server.chmod(WRITABLE)


def test_it_names_its_ports_and_mock_servers_when_it_listens(tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (_, started):
        assert started["mocks"] == ["room-vendor", "second-vendor"]


def test_what_it_prints_does_not_hold_the_token(tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (_, started):
        assert "sample-token" not in json.dumps(started)


def test_the_control_interface_answers_in_the_process(tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (_, started):
        assert client_of(started).control("/mocks/room-vendor/log", token="wrong").status == 401


@pytest.mark.parametrize("signal_number", [signal.SIGTERM, signal.SIGINT])
def test_a_signal_exits_cleanly_when_idle(signal_number: signal.Signals, tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (process, _):
        process.send_signal(signal_number)
        assert process.wait(timeout=GENEROUS_WAIT_S) == EXIT_CLEAN


def test_sigterm_does_not_wait_for_a_request_being_answered(tmp_path: Path):
    config = write_config(tmp_path, with_held_scenarios(sample_document()))
    with running(copied_alone(tmp_path), config) as (process, started):
        client = client_of(started)
        client.set_scenario("room-vendor", "held")
        with client.hold_a_request(AVAILABILITY, "room-vendor"):
            process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=GENEROUS_WAIT_S) == EXIT_CLEAN


def test_sigterm_leaves_no_error_behind(tmp_path: Path):
    with running(copied_alone(tmp_path), SAMPLE_CONFIG) as (process, _):
        process.send_signal(signal.SIGTERM)
        _, errors = process.communicate(timeout=GENEROUS_WAIT_S)
    assert errors == ""


def test_a_bad_config_exits_2_naming_the_place(tmp_path: Path):
    document = sample_document()
    document["mocks"]["room-vendor"]["routes"][0]["method"] = "get"
    config = write_config(tmp_path, document)
    result = subprocess.run(
        on_any_port(copied_alone(tmp_path), config),
        capture_output=True,
        text=True,
        timeout=GENEROUS_WAIT_S,
        check=False,
    )
    assert (result.returncode, "routes[0].method" in result.stderr) == (2, True)


def test_a_missing_config_exits_2_naming_the_file(tmp_path: Path):
    result = subprocess.run(
        on_any_port(copied_alone(tmp_path), tmp_path / "absent.json"),
        capture_output=True,
        text=True,
        timeout=GENEROUS_WAIT_S,
        check=False,
    )
    assert (result.returncode, "absent.json" in result.stderr) == (2, True)


def test_a_port_already_taken_exits_1_saying_so(tmp_path: Path):
    server = copied_alone(tmp_path)
    with running(server, SAMPLE_CONFIG) as (_, started):
        result = subprocess.run(
            command(
                server,
                str(SAMPLE_CONFIG),
                "--bind",
                "127.0.0.1",
                "--api-port",
                str(started["api_port"]),
                "--control-port",
                "0",
            ),
            capture_output=True,
            text=True,
            timeout=GENEROUS_WAIT_S,
            check=False,
        )
    assert (result.returncode, "cannot listen" in result.stderr) == (1, True)


def test_the_ports_default_to_those_of_the_compose_template():
    _, listen = parse_options(["mocks.json"])
    assert listen == ListenOn("0.0.0.0", 8080, 9000)


def test_the_options_set_the_address_and_ports():
    _, listen = parse_options(
        ["mocks.json", "--bind", "127.0.0.1", "--api-port", "1", "--control-port", "2"]
    )
    assert listen == ListenOn("127.0.0.1", 1, 2)


def test_the_config_path_is_the_first_argument():
    path, _ = parse_options(["/cstudy/config/mocks.json"])
    assert path == Path("/cstudy/config/mocks.json")
