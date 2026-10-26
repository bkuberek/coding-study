"""Generated stubs and conformance references must type-check in the real workspace setup."""

import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker
from coding_study.application.ports import ProbeResult
from tests.helpers import REPOSITORY_ROOT
from tests.stub_contract import GOLDEN_ROOT

SUPPORT_MODULE = REPOSITORY_ROOT / "runners" / "typescript" / "support.ts"
CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("pnpm") is None, reason="needs pnpm"),
]


@pytest.fixture(scope="module")
def installed(practice_workspace: Path) -> Path:
    """The practice workspace's TypeScript project, with its `node_modules`."""
    return practice_workspace / "typescript"


def type_check(project: Path) -> ProbeResult:
    result = PnpmTypeChecker().check(project)
    assert result is not None, "pnpm is not installed"
    return result


def mirror_project(directory: Path, installed: Path, practice_files: Mapping[str, Path]) -> Path:
    """A copy of the installed project whose practice/ holds only `practice_files`."""
    for name in ("package.json", "tsconfig.json"):
        shutil.copyfile(installed / name, directory / name)
    (directory / "node_modules").symlink_to(installed / "node_modules")
    (directory / "support.ts").write_text(f'export * from "{SUPPORT_MODULE}";\n')
    practice = directory / "practice"
    practice.mkdir()
    for name, source in practice_files.items():
        shutil.copyfile(source, practice / name)
    return directory


def test_every_golden_stub_type_checks(tmp_path, installed):
    goldens = {path.name: path for path in (GOLDEN_ROOT / "typescript").glob("*.ts")}
    result = type_check(mirror_project(tmp_path, installed, goldens))
    assert result.exit_code == 0, result.output


def test_every_conformance_reference_type_checks(tmp_path, installed):
    references = {
        f"{path.parents[1].name}-{path.name}": path for path in CONFORMANCE.glob("*/solutions/*.ts")
    }
    result = type_check(mirror_project(tmp_path, installed, references))
    assert result.exit_code == 0, result.output


def test_type_errors_fail_the_check(tmp_path, installed):
    broken = tmp_path / "broken.ts"
    broken.write_text('export const answer: number = "forty-two";\n')
    project = tmp_path / "project"
    project.mkdir()
    result = type_check(mirror_project(project, installed, {"broken.ts": broken}))
    assert "practice/broken.ts(1,14): error TS2322" in result.output
