"""The language-server sidecar through a scripted Docker runner
(docs/specs/service-projects.md#language-servers): the exact commands, the compose file it writes,
and a sidecar that is gone after its block however the block ends."""

import json
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters import docker_sandbox
from coding_study.adapters.docker_sandbox import DockerSandbox
from coding_study.application.ports import ProbeResult
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    SIDECAR_SERVICE,
    SandboxUser,
    SharedFolder,
    SidecarPlan,
    SidecarToolchain,
    StackIdentity,
    StackKind,
)
from tests.sandbox_fakes import ScriptedDocker

NAME = "cstudy-l-41-abc"
COMPOSE = ("docker", "compose", "--ansi", "never", "-p", NAME)


@dataclass
class Guards:
    """What stood in for `StackGuard`, whose process would take the sidecar down if this one
    died: each guard made, by its stack, `-v` and run folder, and each released."""

    made: list[tuple[str, bool, Path | None]] = field(
        default_factory=list[tuple[str, bool, Path | None]]
    )
    released: list[str] = field(default_factory=list[str])

    def __call__(
        self, stack: str, *, removes_volumes: bool, environment: object, run_directory: Path
    ) -> AbstractContextManager[None]:
        self.made.append((stack, removes_volumes, run_directory))
        return self._held(stack)

    @contextmanager
    def _held(self, stack: str) -> Iterator[None]:
        try:
            yield
        finally:
            self.released.append(stack)


@pytest.fixture(autouse=True)
def guard(monkeypatch: pytest.MonkeyPatch) -> Guards:
    guards = Guards()
    monkeypatch.setattr(docker_sandbox, "StackGuard", guards)
    return guards


@pytest.fixture
def plan(tmp_path: Path) -> SidecarPlan:
    project = tmp_path / "projects" / "rooms"
    project.mkdir(parents=True)
    servers = tmp_path / ".cs" / "lsp"
    servers.mkdir(parents=True)
    return SidecarPlan(
        identity=StackIdentity(NAME, StackKind.LSP, "d1g3st", "rooms", 41),
        user=SandboxUser(501, 20),
        project=SharedFolder(str(project), str(project)),
        servers=SharedFolder(str(servers), str(servers)),
        run=str(tmp_path / ".cs" / "runs" / NAME),
    )


def stack_file(plan: SidecarPlan) -> str:
    return str(Path(plan.run) / "stack.yaml")


def test_the_sidecar_comes_up_detached_from_its_own_compose_file_and_pulls_nothing(plan):
    docker = ScriptedDocker()

    with DockerSandbox(docker).sidecar(plan):
        pass

    assert (*COMPOSE, "-f", stack_file(plan), "up", "--detach", "--pull", "never") in (
        docker.commands
    )


def test_the_compose_file_holds_the_sidecar(plan):
    written: list[dict[str, object]] = []

    with DockerSandbox(ScriptedDocker()).sidecar(plan):
        written.append(json.loads(Path(stack_file(plan)).read_text()))

    assert list(written[0]["services"]) == [SIDECAR_SERVICE]  # type: ignore[call-overload]


def test_the_sidecar_is_taken_down_after_its_block(plan):
    docker = ScriptedDocker()

    with DockerSandbox(docker).sidecar(plan):
        assert docker.ran("down") == []

    assert docker.ran(*COMPOSE, "down") == [(*COMPOSE, "down")]


def test_the_sidecars_folder_goes_with_it(plan):
    with DockerSandbox(ScriptedDocker()).sidecar(plan):
        pass

    assert not Path(plan.run).exists()


def test_the_sidecar_is_taken_down_when_its_block_fails(plan):
    docker = ScriptedDocker()

    with pytest.raises(RuntimeError), DockerSandbox(docker).sidecar(plan):
        raise RuntimeError("the session ended badly")

    assert docker.ran(*COMPOSE, "down")


def test_a_guard_takes_the_sidecar_down_if_this_process_dies(plan, guard):
    with DockerSandbox(ScriptedDocker()).sidecar(plan):
        assert guard.made == [(NAME, False, Path(plan.run))]


def test_the_guard_is_released_after_the_down(plan, guard):
    with DockerSandbox(ScriptedDocker()).sidecar(plan):
        pass

    assert guard.released == [NAME]


def test_a_sidecar_that_does_not_come_up_says_why_and_leaves_nothing(plan):
    docker = ScriptedDocker()
    docker.answer(("up", "--detach"), ProbeResult(1, "Error: no such image\n"))

    with pytest.raises(SandboxError, match="no such image"), DockerSandbox(docker).sidecar(plan):
        pass

    assert (docker.ran(*COMPOSE, "down"), Path(plan.run).exists()) == ([(*COMPOSE, "down")], False)


def test_a_missing_docker_is_said(plan):
    with (
        pytest.raises(SandboxError, match="docker is not installed"),
        DockerSandbox(ScriptedDocker(missing=True)).sidecar(plan),
    ):
        pass


def test_a_server_runs_in_the_sidecar_through_docker_exec_with_its_standard_input(plan):
    command = DockerSandbox(ScriptedDocker()).sidecar_command(
        plan, ("node", "cli.mjs", "--stdio"), {}
    )

    assert command == (
        "docker",
        "exec",
        "--interactive",
        "--workdir",
        plan.project.path,
        NAME,
        "node",
        "cli.mjs",
        "--stdio",
    )


def test_the_servers_own_variables_cross_docker_exec(plan):
    command = DockerSandbox(ScriptedDocker()).sidecar_command(
        plan, ("java", "-jar", "launcher.jar"), {"XDG_CACHE_HOME": "/data/cache"}
    )

    assert command[: command.index(NAME)][-2:] == ("--env", "XDG_CACHE_HOME=/data/cache")


@pytest.fixture
def jvm_plan(plan: SidecarPlan) -> SidecarPlan:
    """JDT LS's sidecar, on the project's image, with Gradle's files in its data folder."""
    toolchain = SidecarToolchain(
        cache_volume="cstudy-i-rooms-d1g3st_cache",
        environment={},
        files={"gradle/gradle.properties": "org.gradle.projectcachedir=x\n"},
        writable_project=True,
    )
    return replace(plan, image="gradle:9.8.2-jdk25-alpine", toolchain=toolchain)


def test_the_toolchains_files_are_in_the_data_folder_while_the_sidecar_is_up(jvm_plan):
    written: list[str] = []

    with DockerSandbox(ScriptedDocker()).sidecar(jvm_plan):
        written.append((Path(jvm_plan.run) / "data/gradle/gradle.properties").read_text())

    assert written == ["org.gradle.projectcachedir=x\n"]


def test_a_writable_projects_devcontainer_folder_is_there_for_its_read_only_mount(jvm_plan):
    with DockerSandbox(ScriptedDocker()).sidecar(jvm_plan):
        pass

    assert (Path(jvm_plan.project.path) / ".devcontainer").is_dir()


def test_a_link_at_a_writable_projects_devcontainer_is_refused(jvm_plan, tmp_path):
    (Path(jvm_plan.project.path) / ".devcontainer").symlink_to(tmp_path)

    with (
        pytest.raises(SandboxError, match="symbolic link"),
        DockerSandbox(ScriptedDocker()).sidecar(jvm_plan),
    ):
        pass


def test_the_images_own_volumes_get_a_temporary_folder_each(jvm_plan):
    docker = ScriptedDocker()
    docker.answer(("image", "inspect"), ProbeResult(0, '{"/home/gradle/.gradle": {}}\n'))
    written: list[dict[str, Any]] = []

    with DockerSandbox(docker).sidecar(jvm_plan):
        written.append(json.loads(Path(stack_file(jvm_plan)).read_text()))

    tmpfs = written[0]["services"][SIDECAR_SERVICE]["tmpfs"]
    assert tmpfs[1].startswith("/home/gradle/.gradle:")
