"""Real workspaces for the slow tests, outside the repository
(docs/specs/installation-and-workspaces.md#developing-coding-study).

One workspace per session is set up the way a user's is, with the `cstudy init` scaffold and the
`cstudy doctor --fix` steps. Modules that write practice files get a light copy of it: their own
config files and JVM project, with the venv, `node_modules` and runner runtime linked.
"""

import shutil
import subprocess
from pathlib import Path

from coding_study.adapters.runner_runtime import RUNTIME_DIRECTORY
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.application.doctor import JVM_FIX, PYTHON_FIX, TYPESCRIPT_FIX
from tests.helpers import REPOSITORY_ROOT, mark_workspace

TEST_VERSION = "test"
SETUP_STEPS = (PYTHON_FIX, TYPESCRIPT_FIX, JVM_FIX)
JVM_COPY_IGNORED = shutil.ignore_patterns("build", ".gradle", ".kotlin", "src")
TYPESCRIPT_PROJECT_FILES = ("package.json", "tsconfig.json", "support.ts")


def set_up_workspace(root: Path) -> Path:
    """`root` as a ready workspace over this checkout's runners; raises CalledProcessError when
    a toolchain step fails."""
    setup = FsWorkspaceSetup(REPOSITORY_ROOT / "runners", TEST_VERSION)
    setup.write_missing(root)
    setup.refresh_runtime(root)
    for step in SETUP_STEPS:
        subprocess.run(step.command, cwd=root / step.project, check=True, capture_output=True)
    return root


def workspace_like(practice: Path, destination: Path) -> Path:
    """A workspace at `destination` sharing `practice`'s toolchains and runner runtime."""
    mark_workspace(destination, TEST_VERSION)
    python = destination / "python"
    python.mkdir(parents=True)
    shutil.copyfile(practice / "python" / "pyproject.toml", python / "pyproject.toml")
    (python / ".venv").symlink_to(practice / "python" / ".venv", target_is_directory=True)
    typescript = destination / "typescript"
    typescript.mkdir()
    for name in TYPESCRIPT_PROJECT_FILES:
        shutil.copyfile(practice / "typescript" / name, typescript / name)
    (typescript / "node_modules").symlink_to(
        practice / "typescript" / "node_modules", target_is_directory=True
    )
    shutil.copytree(practice / "jvm", destination / "jvm", ignore=JVM_COPY_IGNORED, symlinks=True)
    runtime = destination / RUNTIME_DIRECTORY
    runtime.symlink_to(practice / RUNTIME_DIRECTORY, target_is_directory=True)
    return destination
