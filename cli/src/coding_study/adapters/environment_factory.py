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
from coding_study.adapters.deprecation_warnings import warn_about_deprecated_use
from coding_study.adapters.docker_sandbox import DockerSandbox
from coding_study.adapters.document_index import INDEX_FILE, DocumentIndex
from coding_study.adapters.env_editor import EnvEditorOpener
from coding_study.adapters.fs_calibration_cache import FsCalibrationCache, local_machine_id
from coding_study.adapters.fs_case_cache import FsGeneratedCaseCache
from coding_study.adapters.fs_guide_catalog import FsGuideCatalog
from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.adapters.fs_user_docs import FsUserDocs
from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.jdk_locator import EnvJdkSelector, JdkHome
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.locations import (
    ContentRoot,
    catalog_cache_directory,
    find_content_root,
    find_workspace,
    workspace_directory,
)
from coding_study.adapters.path_toolchain_check import PathToolchainCheck
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.problem_overlay import (
    OverlayItemRepository,
    OverlayProblemFiles,
    OverlayProblemRepository,
)
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.adapters.sqlite.ai_rows import SqliteAiStore
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.adapters.system_clock import SystemClock
from coding_study.adapters.system_machine import SystemMachine
from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.adapters.toml_credentials import open_credentials
from coding_study.adapters.toolchains import RegistryToolchains, RuntimeToolchains
from coding_study.adapters.watchfiles_watcher import WatchfilesWatcher
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.adapters.workspace_marker import has_marker, read_marker
from coding_study.adapters.yaml_problem_sets import YamlProblemSets
from coding_study.application.ai_ports import LanguageModels
from coding_study.application.environment import Environment, ProblemDestination
from coding_study.application.ports import Toolchains
from coding_study.domain.ai import AI_OFF, ApiKey, Provider
from coding_study.domain.ai_models import ModelReply, ModelRequest
from coding_study.domain.config import Config
from coding_study.domain.deprecations import DEPRECATIONS
from coding_study.domain.errors import UsageError
from coding_study.domain.layout import RUNS_DIRECTORY

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


def workspace_toolchains(content: Path, workspace: Path, jdk: JdkHome) -> Toolchains:
    """The language toolchains of `workspace`, building against its runner runtime; Java and
    Kotlin build and run with `jdk`."""
    runtime = RunnerRuntime(content / RUNNERS_DIRECTORY, workspace)
    context = LanguageContext(workspace, runtime.directory, jdk)
    return RuntimeToolchains(RegistryToolchains(LANGUAGES, context), runtime)


def _has_workspace(cwd: Path, environ: Mapping[str, str]) -> bool:
    return has_marker(workspace_directory(cwd, environ))


@dataclass(frozen=True, slots=True)
class _User:
    config: Config
    environ: Mapping[str, str]
    home: Path


def _user(environ: Mapping[str, str], home: Path) -> _User:
    source = TomlConfigSource(config_path(environ, home))
    config = source.load()
    warn_about_deprecated_use(environ, source, DEPRECATIONS)
    return _User(config, environ, home)


def _environment(content: ContentRoot, workspace: Path, user: _User) -> Environment:
    config = user.config
    index = DocumentIndex(workspace / INDEX_FILE)
    catalog = FsProblemRepository(content.path, index=index)
    jdk = EnvJdkSelector(user.environ)
    return Environment(
        root=workspace,
        content_root=content.path,
        config=config,
        problems=OverlayProblemRepository(catalog, workspace),
        files=OverlayProblemFiles(FsProblemFiles(content.path), workspace),
        progress=SqliteProgressStore(
            workspace / config.progress_db,
            config.schedule.mastered_interval_days,
            workspace=workspace,
        ),
        toolchains=workspace_toolchains(content.path, workspace, jdk),
        jdk=jdk,
        toolchain_check=PathToolchainCheck(user.environ, workspace),
        runner_process=SubprocessRunner(workspace / RUNS_DIRECTORY),
        workspace=WorkspaceFs(workspace),
        content_code=ContentCodeLoader(content.path),
        case_cache=FsGeneratedCaseCache(workspace),
        calibrations=FsCalibrationCache(workspace, local_machine_id()),
        clock=SystemClock(),
        editor=EnvEditorOpener(user.environ),
        watcher=WatchfilesWatcher(),
        items=OverlayItemRepository(FsItemRepository(content.path, index), workspace),
        guides=FsGuideCatalog(content.path),
        docs=FsUserDocs(content.path),
        machine=SystemMachine(),
        new_problems=_new_problems(content, workspace),
        study_guides=FsStudyGuides.from_setting(config.study_guides.root, user.home),
        language_servers=LspDirectory(workspace, SubprocessToolProbe(), SubprocessCommandRunner()),
        sandbox=DockerSandbox(runs_directory=workspace / RUNS_DIRECTORY),
        stack_clients=open_stack_clients,
        problem_sets=YamlProblemSets(WorkspaceFs(workspace)),
        preferences=FsPreferencesStore(workspace),
        ai_store=SqliteAiStore(workspace / config.progress_db, workspace),
        credentials=open_credentials(user.environ, user.home, workspace),
        models=_language_models(config.ai.enabled, user.environ),
        workspace_languages=read_marker(workspace).languages if has_marker(workspace) else None,
    )


class NoLanguageModels:
    """The port with `ai.enabled` false: it refuses every request, and nothing of
    `coding_study.adapters.ai` is imported (docs/specs/ai.md#with-ai-off)."""

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        raise UsageError(AI_OFF)

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        raise UsageError(AI_OFF)


class _LoadedOnUse:
    """The port with `ai.enabled` true: the provider adapters are imported at the first request,
    so no command that sends nothing pays for them."""

    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environ = environ
        self._models: LanguageModels | None = None

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        return self._loaded().complete(request, key)

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        return self._loaded().list_models(provider, key, deadline_s)

    def _loaded(self) -> LanguageModels:
        if self._models is None:
            from coding_study.adapters.ai.models import open_language_models

            self._models = open_language_models(self._environ)
        return self._models


def _language_models(enabled: bool, environ: Mapping[str, str]) -> LanguageModels:
    return _LoadedOnUse(environ) if enabled else NoLanguageModels()


def _new_problems(content: ContentRoot, workspace: Path) -> ProblemDestination:
    root = content.path if content.editable else workspace
    return ProblemDestination(FsProblemFiles(root), WorkspaceFs(root))
