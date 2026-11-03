"""`cstudy doctor` (docs/specs/cli.md#cstudy-doctor)."""

import json
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.cstudy_installs import PathCstudyInstalls
from coding_study.adapters.environment_factory import RUNNERS_DIRECTORY
from coding_study.adapters.jdk_locator import EnvJdkSelector
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_servers import InstalledDebugServers, Machine
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.locations import (
    ContentRootError,
    FsRepositoryFiles,
    WorkspaceError,
    find_content_root,
    find_workspace,
    workspace_directory,
)
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.serve_install import InstalledWebUi
from coding_study.adapters.sqlite.progress_database import SqliteProgressDatabase
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.adapters.toolchains import RegistryToolchains
from coding_study.adapters.workspace_marker import has_marker, read_marker, tool_version
from coding_study.adapters.workspace_setup import FsProjectLinks, FsWorkspaceSetup
from coding_study.application.doctor import (
    CheckResult,
    CheckStatus,
    ContentLocation,
    DoctorEnvironment,
    DoctorReport,
    FixOutcome,
    NotFound,
    PracticeWorkspace,
    fix_workspace,
    repair_workspace,
    run_doctor,
)
from coding_study.application.ports import ProgressNotice
from coding_study.domain.cases import JsonValue
from coding_study.domain.config import Config
from coding_study.domain.errors import ConfigError, UsageError
from coding_study.domain.layout import RUNS_DIRECTORY
from coding_study.entrypoints.shared import ExitCode, add_command, command_environ, console
from coding_study.entrypoints.web import STATIC_DIRECTORY

NAME = "doctor"
STATUS_LABEL_WIDTH = 6
FIX_SEPARATOR = "    fix: "
FIX_OUTPUT_LINES = 10
_STATUS_STYLES = {
    CheckStatus.OK: ("ok", "green"),
    CheckStatus.WARN: ("WARN", "yellow"),
    CheckStatus.FAIL: ("FAIL", "bold red"),
}


def register(app: typer.Typer) -> None:
    add_command(app, doctor, NAME)


def doctor(
    context: typer.Context,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help=(
                "First run uv sync (and add pytest when the venv lacks it), pnpm install and the "
                "Gradle build in the workspace projects, and migrate progress.db."
            ),
        ),
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the rows.")
    ] = False,
) -> None:
    """Check toolchains, the config file and the workspace setup."""
    if as_json and fix:
        raise UsageError("--json excludes --fix")
    environment = doctor_environment(Path.cwd(), command_environ(context), Path.home())
    if as_json:
        _print_document(environment)
        return
    output = console(context)
    fixes_failed = fix and not _fix(environment, output)
    report = run_doctor(environment, _notice(output))
    for result in report.results:
        output.print(_check_line(result))
    if fixes_failed or not report.passed:
        raise typer.Exit(ExitCode.ENVIRONMENT_ERROR)


def _print_document(environment: DoctorEnvironment) -> None:
    """The checks as one document; notices go to standard error."""
    report = run_doctor(environment, _error_notice)
    typer.echo(json.dumps(doctor_document(environment, report), indent=2))
    if not report.passed:
        raise typer.Exit(ExitCode.ENVIRONMENT_ERROR)


def doctor_document(environment: DoctorEnvironment, report: DoctorReport) -> dict[str, JsonValue]:
    """`cstudy doctor --json`."""
    workspace = environment.workspace
    root = None if isinstance(workspace, NotFound) else str(workspace.files.root)
    checks: list[JsonValue] = [
        {
            "name": result.name,
            "status": result.status.value,
            "detail": result.detail,
            "fix": result.fix,
        }
        for result in report.results
    ]
    return {"workspace": root, "passed": report.passed, "checks": checks}


def _error_notice(line: str) -> None:
    typer.echo(line, err=True)


def doctor_environment(cwd: Path, environ: Mapping[str, str], home: Path) -> DoctorEnvironment:
    content = _content(environ)
    config = TomlConfigSource(config_path(environ, home))
    version = tool_version()
    return DoctorEnvironment(
        tools=SubprocessToolProbe(),
        jdk=EnvJdkSelector(environ),
        debug_servers=InstalledDebugServers(Machine(environ, home)),
        config=config,
        content=content,
        workspace=_workspace(cwd, environ, content, config),
        version=version,
        web=InstalledWebUi(STATIC_DIRECTORY),
        installs=PathCstudyInstalls(environ, home, Path(sys.prefix), version),
    )


def _content(environ: Mapping[str, str]) -> ContentLocation | NotFound:
    try:
        content = find_content_root(environ)
    except ContentRootError as error:
        return NotFound(str(error))
    return ContentLocation(FsRepositoryFiles(content.path), content.editable)


def _workspace(
    cwd: Path,
    environ: Mapping[str, str],
    content: ContentLocation | NotFound,
    config: TomlConfigSource,
) -> PracticeWorkspace | NotFound:
    try:
        root = find_workspace(cwd, environ)
    except WorkspaceError as error:
        return NotFound(str(error), unusable=has_marker(workspace_directory(cwd, environ)))
    content_root = content.files.root if isinstance(content, ContentLocation) else root
    language_servers = LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner())
    return PracticeWorkspace(
        files=FsRepositoryFiles(root),
        created_with=read_marker(root).created_with,
        setup=FsWorkspaceSetup(content_root / RUNNERS_DIRECTORY, tool_version()),
        toolchains=RegistryToolchains(LANGUAGES, LanguageContext(root, root / RUNTIME_RUNNERS)),
        runner_process=SubprocessRunner(root / RUNS_DIRECTORY),
        commands=SubprocessCommandRunner(),
        project_links=FsProjectLinks(),
        progress=SqliteProgressDatabase(root / _progress_db(config)),
        preferences=FsPreferencesStore(root),
        language_servers=language_servers,
        language_server_installer=language_servers,
    )


def _progress_db(config: TomlConfigSource) -> str:
    """The configured file; an invalid config is the `config` row's to report, so the default."""
    try:
        return config.load().progress_db
    except ConfigError:
        return Config().progress_db


def _fix(environment: DoctorEnvironment, output: Console) -> bool:
    """Run every setup command; True when all of them succeeded."""
    workspace = environment.workspace
    if isinstance(workspace, NotFound):
        raise WorkspaceError(workspace.reason)
    repair_workspace(workspace, _notice(output))
    outcomes = fix_workspace(workspace, environment.content, environment.jdk, _notice(output))
    for outcome in outcomes:
        for line in _fix_lines(outcome):
            output.print(line)
    return all(outcome.succeeded for outcome in outcomes)


def _fix_lines(outcome: FixOutcome) -> Iterator[Text]:
    status = CheckStatus.OK if outcome.succeeded else CheckStatus.FAIL
    manual = None if outcome.succeeded else outcome.step.manual
    yield _check_line(CheckResult(str(outcome.step), status, outcome.detail, fix=manual))
    if outcome.succeeded or outcome.result is None:
        return
    for line in outcome.result.output.splitlines()[-FIX_OUTPUT_LINES:]:
        yield Text(f"{' ' * STATUS_LABEL_WIDTH}{line}", style="dim")


def _notice(output: Console) -> ProgressNotice:
    def notice(line: str) -> None:
        output.print(Text(line, style="dim"))

    return notice


def _check_line(result: CheckResult) -> Text:
    label, style = _STATUS_STYLES[result.status]
    line = Text(label.ljust(STATUS_LABEL_WIDTH), style=style)
    line.append(result.name)
    if result.detail:
        line.append(f" {result.detail}")
    if result.fix:
        line.append(f"{FIX_SEPARATOR}{result.fix}", style="dim")
    return line
