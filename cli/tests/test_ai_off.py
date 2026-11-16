"""With AI off nothing leaves the machine (docs/specs/ai.md#with-ai-off).

Real child `cstudy` processes run with a probe in `sitecustomize` (`tests/ai_off_site`) that
refuses any connection or name lookup off the loopback and records what each child did. The config
has AI off, a model, and a consent, and `credentials.toml` holds a sentinel key for every provider,
so AI being off is the only thing that refuses a request. The sentinels are searched in every
output and every file of the workspace.
"""

import json
import os
import signal
import subprocess
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from coding_study.domain.ai import AI_OFF, Provider
from coding_study.entrypoints.shared import ExitCode
from tests.serve_page import opened_page
from tests.serve_process import running_server

SITE = Path(__file__).resolve().parent / "ai_off_site"
LOG_VARIABLE = "AI_OFF_PROBE_LOG"
SLUG = "url-shortener"
NOTES = f"notes/system-design/{SLUG}.md"
ANSWER = "## Requirements\n\nRedirects stay fast even when creating links is down.\n"
MODEL = "anthropic:model-x"
SENTINELS = {provider: f"ai-off-sentinel-{provider}-9c41d7e2b6a3f580" for provider in Provider}
CREDENTIALS = "".join(f'[{provider}]\napi_key = "{key}"\n\n' for provider, key in SENTINELS.items())
CONFIG = f'[ai]\nenabled = false\nrouting = "fixed"\nmodel = "{MODEL}"\n'
RUN_SECONDS = 300
OFF_STATUS = (
    "off: nothing is sent; turn it on with ai.enabled = true (cstudy config edit) or in Settings"
)
AI_JOBS = (
    {"command": "ai_review", "slug": SLUG, "confirm": True},
    {"command": "ai_check", "confirm": True},
    {"command": "ai_models", "provider": "anthropic"},
)
DOCTOR_EXITS = (ExitCode.SUCCESS, ExitCode.FAILURES, ExitCode.ENVIRONMENT_ERROR)
"""A workspace without its toolchains set up fails rows that have nothing to do with AI."""
AI_COMMANDS = ("ai", "doctor")
"""The commands that may read `credentials.toml`."""


@dataclass(frozen=True)
class Probe:
    """What one child process recorded when it exited."""

    refused: list[str]
    credential_reads: list[str]
    provider_modules: list[str]

    @classmethod
    def of(cls, line: Mapping[str, list[str]]) -> "Probe":
        return cls(line["refused"], line["credential_reads"], line["provider_modules"])


def probes_in(log: Path) -> list[Probe]:
    if not log.exists():
        return []
    return [Probe.of(json.loads(line)) for line in log.read_text().splitlines()]


@dataclass(frozen=True)
class Run:
    arguments: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    probes: list[Probe]

    @property
    def text(self) -> str:
        return self.stdout + self.stderr


@dataclass
class Machine:
    """A workspace and a config directory with AI off, and a way to run `cstudy` over them."""

    root: Path
    runs: list[Run] = field(default_factory=list[Run])

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def config(self) -> Path:
        return self.root / "config" / "config.toml"

    def environment(self, log: Path) -> dict[str, str]:
        inherited = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("CSTUDY_") and name != "PYTHONPATH"
        }
        path = os.pathsep.join(filter(None, [str(SITE), os.environ.get("PYTHONPATH", "")]))
        return {
            **inherited,
            "PYTHONPATH": path,
            "CSTUDY_CONFIG": str(self.config),
            "CSTUDY_WORKSPACE": str(self.workspace),
            LOG_VARIABLE: str(log),
            "NO_COLOR": "1",
            "COLUMNS": "200",
        }

    def log(self) -> Path:
        logs = self.root / "logs"
        logs.mkdir(exist_ok=True)
        return logs / f"{len(self.runs)}.jsonl"

    def run(self, *arguments: str, stdin: str = "") -> Run:
        log = self.log()
        done = subprocess.run(
            [sys.executable, "-m", "coding_study", *arguments],
            input=stdin,
            capture_output=True,
            text=True,
            env=self.environment(log),
            timeout=RUN_SECONDS,
            check=False,
        )
        run = Run(arguments, done.returncode, done.stdout, done.stderr, probes_in(log))
        self.runs.append(run)
        return run

    def ran(self, *arguments: str) -> Run:
        return next(run for run in self.runs if run.arguments == arguments)

    def files(self) -> Iterator[Path]:
        yield from (path for path in self.workspace.rglob("*") if path.is_file())
        yield from (path for path in self.root.joinpath("logs").glob("*") if path.is_file())


def machine_in(root: Path) -> Machine:
    machine = Machine(root)
    machine.config.parent.mkdir(parents=True)
    machine.config.write_text(CONFIG)
    machine.config.with_name("credentials.toml").write_text(CREDENTIALS)
    return machine


def with_workspace(machine: Machine) -> Machine:
    init = machine.run("init", str(machine.workspace), "--lang", "python", "--no-ide")
    assert init.exit_code == ExitCode.SUCCESS, init.text
    return machine


@pytest.fixture(scope="module")
def tour(tmp_path_factory: pytest.TempPathFactory) -> Machine:
    """Every AI surface and the common commands, run once, in the order a learner meets them."""
    machine = with_workspace(machine_in(tmp_path_factory.mktemp("ai-off")))
    run = machine.run
    run("list")
    run("start", SLUG, "--no-open")
    (machine.workspace / NOTES).write_text(ANSWER)
    run("status")
    run("ai", "status")
    run("ai", "status", "--json")
    run("ai", "usage")
    run("ai", "usage", "--json")
    run("ai", "consent", MODEL, "--purpose", "review")
    run("ai", "key", "anthropic", stdin=f"{SENTINELS[Provider.ANTHROPIC]}\n")
    for provider in Provider:
        run("ai", "models", str(provider))
    run("ai", "check")
    run("ai", "review", "--dry-run")
    run("ai", "review")
    run("ai", "review", "--json")
    run("ai", "review", "--list")
    run("doctor")
    run("done", "--rating", "ok")
    run("history", SLUG)
    run("export")
    return machine


def sent_nothing(run: Run) -> None:
    assert run.probes, f"{run.arguments}: the probe left no record: the child was not guarded"
    assert [probe.refused for probe in run.probes] == [[]] * len(run.probes)


# The probe


def test_the_probe_refuses_a_connection_off_the_loopback_and_records_it(tmp_path):
    log = tmp_path / "probe.jsonl"
    code = (
        "import socket\n"
        "for connect in (lambda: socket.socket().connect(('192.0.2.1', 443)),\n"
        "                lambda: socket.getaddrinfo('example.com', 443)):\n"
        "    try:\n"
        "        connect()\n"
        "    except RuntimeError as refusal:\n"
        "        print('refused')\n"
        "listener = socket.create_server(('127.0.0.1', 0))\n"
        "socket.create_connection(listener.getsockname(), 1).close()\n"
        "open('credentials.toml', 'a').close()\n"
    )
    environment = {**os.environ, "PYTHONPATH": str(SITE), LOG_VARIABLE: str(log)}
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
        check=True,
    )
    [probe] = probes_in(log)
    assert done.stdout.split() == ["refused", "refused"]
    assert [refusal.split(" refused")[0] for refusal in probe.refused] == [
        "socket.connect to ('192.0.2.1', 443)",
        "socket.getaddrinfo for 'example.com'",
    ]
    assert probe.credential_reads == ["credentials.toml"]
    assert probe.provider_modules == []


# The commands


@pytest.mark.slow
def test_every_command_of_the_tour_ran_with_a_probe_and_connected_to_nothing(tour):
    assert tour.runs
    for run in tour.runs:
        sent_nothing(run)


@pytest.mark.slow
@pytest.mark.parametrize(
    "arguments",
    [
        ("ai", "models", "anthropic"),
        ("ai", "models", "google"),
        ("ai", "models", "openai"),
        ("ai", "models", "openrouter"),
        ("ai", "check"),
        ("ai", "review"),
        ("ai", "review", "--json"),
    ],
)
def test_a_command_that_would_send_is_refused_with_the_ai_off_message(tour, arguments):
    run = tour.ran(*arguments)
    assert run.exit_code == ExitCode.USAGE_ERROR
    assert run.stderr.strip() == f"error: {AI_OFF}"
    assert run.stdout == ""


@pytest.mark.slow
def test_the_forms_that_send_nothing_work(tour):
    for arguments in [
        ("ai", "status"),
        ("ai", "status", "--json"),
        ("ai", "usage"),
        ("ai", "usage", "--json"),
        ("ai", "consent", MODEL, "--purpose", "review"),
        ("ai", "key", "anthropic"),
        ("ai", "review", "--dry-run"),
        ("ai", "review", "--list"),
    ]:
        assert tour.ran(*arguments).exit_code == ExitCode.SUCCESS, arguments


@pytest.mark.slow
def test_status_says_ai_is_off_and_the_dry_run_sends_nothing(tour):
    assert OFF_STATUS in tour.ran("ai", "status").stdout
    document = json.loads(tour.ran("ai", "status", "--json").stdout)
    assert document["enabled"] is False
    assert document["credentials"]["keys"] == dict.fromkeys(map(str, Provider), True)
    assert "=== not sent ===" in tour.ran("ai", "review", "--dry-run").stdout
    assert tour.ran("ai", "usage", "--json").exit_code == ExitCode.SUCCESS
    assert json.loads(tour.ran("ai", "usage", "--json").stdout)["total"]["requests"] == 0


@pytest.mark.slow
def test_the_common_commands_work_as_before(tour):
    for arguments in [
        ("list",),
        ("start", SLUG, "--no-open"),
        ("status",),
        ("done", "--rating", "ok"),
        ("history", SLUG),
        ("export",),
    ]:
        run = tour.ran(*arguments)
        assert run.exit_code == ExitCode.SUCCESS, (arguments, run.text)


@pytest.mark.slow
def test_the_doctor_shows_the_ai_row_and_still_checks_the_rest(tour):
    doctor = tour.ran("doctor")
    assert doctor.exit_code in DOCTOR_EXITS, doctor.text
    [row] = [line for line in doctor.stdout.splitlines() if line.split()[1:3] == ["ai", "off"]]
    assert row.startswith("ok")
    assert any(line.startswith("ok") and "python" in line for line in doctor.stdout.splitlines())


# What stays out


@pytest.mark.slow
def test_no_command_imports_a_provider_adapter(tour):
    for run in tour.runs:
        assert [probe.provider_modules for probe in run.probes] == [[]] * len(run.probes), (
            run.arguments
        )


@pytest.mark.slow
def test_only_ai_work_reads_credentials_toml(tour):
    for run in tour.runs:
        reads = [read for probe in run.probes for read in probe.credential_reads]
        if run.arguments[0] in AI_COMMANDS:
            continue
        assert reads == [], run.arguments
    reading = {run.arguments for run in tour.runs if any(p.credential_reads for p in run.probes)}
    assert ("ai", "status") in reading


@pytest.mark.slow
def test_a_key_is_in_no_output_error_or_file(tour):
    files = [(path, path.read_bytes()) for path in tour.files()]
    assert any(path.name == "progress.db" for path, _ in files)
    assert any(path.name == "progress-export.json" for path, _ in files)
    for provider, key in SENTINELS.items():
        needle = key.encode()
        for run in tour.runs:
            assert key not in run.text, (provider, run.arguments)
        assert [path for path, content in files if needle in content] == [], provider


@pytest.mark.slow
def test_the_export_holds_no_ai_record_but_the_reviews(tour):
    export = json.loads((tour.workspace / "progress-export.json").read_text())
    assert export["tables"]["ai_reviews"] == []
    assert not {"ai_calls", "ai_consents"} & set(export["tables"])


# The page


@pytest.mark.slow
def test_the_page_answers_every_ai_job_422_and_sends_nothing(tmp_path):
    machine = with_workspace(machine_in(tmp_path))
    log = tmp_path / "server.jsonl"
    variables = machine.environment(log)
    with running_server(machine.workspace, variables=variables) as server:
        page = opened_page(server)
        assert page.client.get("/api/v1/session").json()["ai"] == {"enabled": False}
        status = page.client.get("/api/v1/ai/status")
        usage = page.client.get("/api/v1/ai/usage")
        assert page.start_attempt(SLUG, None).status_code == 201
        (machine.workspace / NOTES).write_text(ANSWER)
        refusals = [
            page.client.post("/api/v1/jobs", json=job, headers=page.headers) for job in AI_JOBS
        ]
        exit_code, _ = server.stop(signal.SIGINT)
    assert (status.status_code, usage.status_code) == (200, 200)
    assert status.json()["enabled"] is False
    assert [response.status_code for response in refusals] == [422] * len(AI_JOBS)
    assert [response.json()["error"]["message"] for response in refusals] == [AI_OFF] * 3
    assert exit_code == ExitCode.INTERRUPTED
    probes = probes_in(log)
    assert probes
    assert [probe.refused for probe in probes] == [[]] * len(probes)
    assert [probe.provider_modules for probe in probes] == [[]] * len(probes)
    shown = "".join(
        str(response.headers) + response.text for response in [status, usage, *refusals]
    )
    for key in SENTINELS.values():
        assert key not in shown
        assert [path for path in machine.files() if key.encode() in path.read_bytes()] == []
