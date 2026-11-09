"""The service project fixtures on a real workspace and a real Docker engine, driven through the
`cstudy` command line as a learner does, on resources this test labels and removes."""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from tests.waits import GENEROUS_WAIT_S

FIXTURES = Path(__file__).parent / "fixtures" / "service_projects"
NAIVE = FIXTURES / "naive"
TYPESCRIPT = "5901-fixture-rooms-typescript"
PYTHON = "5902-fixture-rooms-python"
MEMBERS = "5903-fixture-members-python"
"""Postgres and Redis as backing services, with `grade_setup` and `reset`."""
CSTUDY = str(Path(sys.executable).with_name("cstudy"))
COMMAND_WAIT_S = 3 * GENEROUS_WAIT_S
"""A command brings a stack up more than once, and may install."""
_LEFT_OUT = shutil.ignore_patterns(".ruff_cache", "__pycache__")
"""Caches a local lint leaves are no part of a starter."""
LABEL_WORKSPACE = "cstudy.workspace"
LABEL_SLUG = "cstudy.slug"


def docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=GENEROUS_WAIT_S,
        check=False,
    )


@dataclass(frozen=True, slots=True)
class FixtureProject:
    directory: str
    root: Path
    """The workspace."""

    @property
    def slug(self) -> str:
        return self.directory.partition("-")[2]

    @property
    def folder(self) -> Path:
        return self.root / "projects" / self.slug

    @property
    def problem(self) -> Path:
        return self.root / "problems" / self.directory

    def environment(self) -> dict[str, str]:
        return {
            **os.environ,
            "CSTUDY_WORKSPACE": str(self.root),
            "CSTUDY_CONFIG": str(self.root.parent / "config.toml"),
            "EDITOR": "true",
        }

    def cstudy(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [CSTUDY, *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=COMMAND_WAIT_S,
            check=False,
            cwd=self.root,
            env=self.environment(),
        )

    def use_overlay(self, overlay: Path) -> None:
        """Your code, written over the project folder."""
        for file in overlay.rglob("*"):
            if file.is_file():
                target = self.folder / file.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, target)

    def use_naive(self) -> None:
        self.use_overlay(NAIVE / self.slug)

    def use_reference(self) -> None:
        self.use_overlay(self.problem / "solutions" / "reference")

    def labelled(self, kind: str) -> list[str]:
        """What Docker holds of this slug, by label; never anything else."""
        label = f"label={LABEL_SLUG}={self.slug}"
        match kind:
            case "containers":
                arguments = ("ps", "-aq", "--filter", label)
            case "networks":
                arguments = ("network", "ls", "-q", "--filter", label)
            case _:
                arguments = ("volume", "ls", "-q", "--filter", label)
        return docker(*arguments).stdout.split()

    def remove_all_it_left(self) -> None:
        """The install cache stays by design, so a test takes it away itself."""
        for container in self.labelled("containers"):
            docker("rm", "-fv", container)
        for network in self.labelled("networks"):
            docker("network", "rm", network)
        for volume in self.labelled("volumes"):
            docker("volume", "rm", volume)


def fixture_project(directory: str, scratch: Path) -> FixtureProject:
    """A workspace of its own, made by `cstudy init`, with the problem among your own problems."""
    root = scratch.resolve() / "workspace"
    project = FixtureProject(directory, root)
    subprocess.run(
        [CSTUDY, "init", str(root), "--no-ide"],
        check=True,
        capture_output=True,
        env=project.environment(),
        timeout=GENEROUS_WAIT_S,
    )
    copy_fixture(directory, project.problem)
    return project


def copy_fixture(directory: str, problem: Path) -> None:
    """The fixture's files at `problem`."""
    shutil.copytree(FIXTURES / directory, problem, ignore=_LEFT_OUT)
