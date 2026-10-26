"""The IntelliJ open-file launcher in a workspace's runtime
(docs/decisions/0010-ide-integration.md)."""

import os
from pathlib import Path

import pytest

from coding_study.adapters.ide.launcher import IdeLauncher, launcher_jar

OLD_NS = 1_000_000_000


@pytest.fixture
def launcher(tmp_path: Path) -> IdeLauncher:
    return IdeLauncher(tmp_path / "runtime")


def test_the_launcher_lives_in_the_runtime_ide_directory(launcher, tmp_path):
    assert launcher.path == tmp_path / "runtime" / "ide" / "cstudy-launcher.jar"


def test_the_shipped_launcher_is_a_jar():
    assert launcher_jar().startswith(b"PK")


def test_a_runtime_without_it_is_not_current(launcher):
    assert launcher.is_current() is False


def test_install_copies_the_shipped_jar(launcher):
    launcher.install()
    assert launcher.path.read_bytes() == launcher_jar()


def test_install_makes_it_current(launcher):
    launcher.install()
    assert launcher.is_current() is True


def test_install_replaces_a_different_file(launcher):
    launcher.path.parent.mkdir(parents=True)
    launcher.path.write_bytes(b"stale")
    launcher.install()
    assert launcher.is_current() is True


def test_install_leaves_a_current_copy_alone(launcher):
    launcher.install()
    os.utime(launcher.path, ns=(OLD_NS, OLD_NS))
    launcher.install()
    assert launcher.path.stat().st_mtime_ns == OLD_NS
