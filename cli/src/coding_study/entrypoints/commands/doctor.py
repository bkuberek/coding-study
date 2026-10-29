"""`cstudy doctor` (docs/specs/cli.md#cstudy-doctor)."""

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import RUNNERS_DIRECTORY
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
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.adapters.toolchains import RegistryToolchains
from coding_study.adapters.workspace_marker import has_marker, read_marker, tool_version
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.application.doctor import (
    CheckResult,
    CheckStatus,
    ContentLocation,
    DoctorEnvironment,
    FixOutcome,
    NotFound,
    PracticeWorkspace,
    fix_workspace,
    repair_workspace,
    run_doctor,
)
from coding_study.application.ports import ProgressNotice
from coding_study.entrypoints.shared import ExitCode, add_command, command_environ, console

NAME = "doctor"
STATUS_LABEL_WIDTH = 6
FIX_SEPARATOR = "    fix: "
FIX_OUTPUT_LINES = 10
RUNS_DIRECTORY = Path(".cs") / "runs"
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
            help="First run uv sync, pnpm install and the Gradle build in the workspace projects.",
        ),
    ] = False,
) -> None:
    """Check toolchains, the config file and the workspace setup."""
    output = console(context)
    environment = doctor_environment(Path.cwd(), command_environ(context), Path.home())
    fixes_failed = fix and not _fix(environment, output)
    report = run_doctor(environment, _notice(output))
    for result in report.results:
        output.print(_check_line(result))
    if fixes_failed or not report.passed:
        raise typer.Exit(ExitCode.ENVIRONMENT_ERROR)


def doctor_environment(cwd: Path, environ: Mapping[str, str], home: Path) -> DoctorEnvironment:
    content = _content(environ)
    return DoctorEnvironment(
        tools=SubprocessToolProbe(),
        debug_servers=InstalledDebugServers(Machine(environ, home)),
        config=TomlConfigSource(config_path(environ, home)),
        content=content,
        workspace=_workspace(cwd, environ, content),
        version=tool_version(),
    )


def _content(environ: Mapping[str, str]) -> ContentLocation | NotFound:
    try:
        content = find_content_root(environ)
    except ContentRootError as error:
        return NotFound(str(error))
    return ContentLocation(FsRepositoryFiles(content.path), content.editable)


def _workspace(
    cwd: Path, environ: Mapping[str, str], content: ContentLocation | NotFound
) -> PracticeWorkspace | NotFound:
    try:
        root = find_workspace(cwd, environ)
    except WorkspaceError as error:
        return NotFound(str(error), unusable=has_marker(workspace_directory(cwd, environ)))
    content_root = content.files.root if isinstance(content, ContentLocation) else root
    return PracticeWorkspace(
        files=FsRepositoryFiles(root),
        created_with=read_marker(root).created_with,
        setup=FsWorkspaceSetup(content_root / RUNNERS_DIRECTORY, tool_version()),
        toolchains=RegistryToolchains(LANGUAGES, LanguageContext(root, root / RUNTIME_RUNNERS)),
        runner_process=SubprocessRunner(root / RUNS_DIRECTORY),
        commands=SubprocessCommandRunner(),
    )


def _fix(environment: DoctorEnvironment, output: Console) -> bool:
    """Run every setup command; True when all of them succeeded."""
    workspace = environment.workspace
    if isinstance(workspace, NotFound):
        raise WorkspaceError(workspace.reason)
    repair_workspace(workspace, _notice(output))
    outcomes = fix_workspace(workspace, environment.content, _notice(output))
    for outcome in outcomes:
        for line in _fix_lines(outcome):
            output.print(line)
    return all(outcome.succeeded for outcome in outcomes)


def _fix_lines(outcome: FixOutcome) -> Iterator[Text]:
    status = CheckStatus.OK if outcome.succeeded else CheckStatus.FAIL
    yield _check_line(CheckResult(str(outcome.step), status, outcome.detail))
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
