"""Builds the `Environment` every practice command runs in, from the real adapters.

The content root and the workspace come from `locations`
(docs/specs/installation-and-workspaces.md).
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from coding_study.adapters.conformance_fixtures import (
    CONFORMANCE_DIRECTORY,
    conformance_repository,
)
from coding_study.adapters.content_code_loader import ContentCodeLoader
from coding_study.adapters.document_index import INDEX_FILE, DocumentIndex
from coding_study.adapters.env_editor import EnvEditorOpener
from coding_study.adapters.fs_calibration_cache import FsCalibrationCache, local_machine_id
from coding_study.adapters.fs_case_cache import FsGeneratedCaseCache
from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.locations import (
    ContentRoot,
    catalog_cache_directory,
    find_content_root,
    find_workspace,
    workspace_directory,
)
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.system_clock import SystemClock
from coding_study.adapters.system_machine import SystemMachine
from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.adapters.toolchains import RegistryToolchains, RuntimeToolchains
from coding_study.adapters.watchfiles_watcher import WatchfilesWatcher
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.adapters.workspace_marker import has_marker
from coding_study.application.environment import Environment, ProblemDestination
from coding_study.application.ports import Toolchains
from coding_study.domain.config import Config
from coding_study.domain.scaffold import WORKSPACE_FIRST_ID

RUNS_DIRECTORY = Path(".cs") / "runs"
RUNNERS_DIRECTORY = "runners"


def load_environment(cwd: Path, environ: Mapping[str, str], home: Path) -> Environment:
    """Raises WorkspaceError outside a workspace, ContentRootError without content and
    ConfigError for a bad config."""
    content = find_content_root(environ)
    workspace = find_workspace(cwd, environ)
    return _environment(content, workspace, _user(environ, home))


def load_catalog_environment(cwd: Path, environ: Mapping[str, str], home: Path) -> Environment:
    """For `cstudy list` and `cstudy show`: the workspace when there is one; otherwise the catalog
    with empty progress, caching in the user cache directory, never in the current directory."""
    if _has_workspace(cwd, environ):
        return load_environment(cwd, environ, home)
    content = find_content_root(environ)
    return _environment(content, catalog_cache_directory(environ, home), _user(environ, home))


def conformance_environment(environment: Environment) -> Environment:
    """The same environment over the runner conformance fixtures in runners/conformance/."""
    return replace(
        environment,
        problems=conformance_repository(environment.content_root),
        files=FsProblemFiles(environment.content_root, CONFORMANCE_DIRECTORY),
    )


def workspace_toolchains(content: Path, workspace: Path) -> Toolchains:
    """The language toolchains of `workspace`, building against its runner runtime."""
    runtime = RunnerRuntime(content / RUNNERS_DIRECTORY, workspace)
    context = LanguageContext(workspace, runtime.directory)
    return RuntimeToolchains(RegistryToolchains(LANGUAGES, context), runtime)


def _has_workspace(cwd: Path, environ: Mapping[str, str]) -> bool:
    return has_marker(workspace_directory(cwd, environ))


@dataclass(frozen=True, slots=True)
class _User:
    config: Config
    environ: Mapping[str, str]
    home: Path


def _user(environ: Mapping[str, str], home: Path) -> _User:
    return _User(TomlConfigSource(config_path(environ, home)).load(), environ, home)


def _environment(content: ContentRoot, workspace: Path, user: _User) -> Environment:
    config = user.config
    index = DocumentIndex(workspace / INDEX_FILE)
    catalog = FsProblemRepository(content.path, index=index)
    return Environment(
        root=workspace,
        content_root=content.path,
        config=config,
        problems=OverlayProblemRepository(catalog, workspace),
        files=OverlayProblemFiles(FsProblemFiles(content.path), workspace),
        progress=SqliteProgressStore(workspace / config.progress_db),
        toolchains=workspace_toolchains(content.path, workspace),
        runner_process=SubprocessRunner(workspace / RUNS_DIRECTORY),
        workspace=WorkspaceFs(workspace),
        content_code=ContentCodeLoader(content.path),
        case_cache=FsGeneratedCaseCache(workspace),
        calibrations=FsCalibrationCache(workspace, local_machine_id()),
        clock=SystemClock(),
        editor=EnvEditorOpener(user.environ),
        watcher=WatchfilesWatcher(),
        items=FsItemRepository(content.path, index),
        machine=SystemMachine(),
        new_problems=_new_problems(content, workspace),
        study_guides=FsStudyGuides.from_setting(config.study_guides.root, user.home),
    )


def _new_problems(content: ContentRoot, workspace: Path) -> ProblemDestination:
    if content.editable:
        return ProblemDestination(FsProblemFiles(content.path), WorkspaceFs(content.path))
    return ProblemDestination(FsProblemFiles(workspace), WorkspaceFs(workspace), WORKSPACE_FIRST_ID)
