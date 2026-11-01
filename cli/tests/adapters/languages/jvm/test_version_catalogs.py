"""The plugins compile against the Kotlin Gradle plugin's API at the workspace's Kotlin version,
which the runners' version catalog repeats: a workspace that built Kotlin has that API cached, so
its runtime upgrades offline (docs/specs/runners.md#the-jdk-and-the-release-level)."""

import tomllib
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT

RUNNERS_CATALOG = REPOSITORY_ROOT / "runners" / "jvm" / "gradle" / "libs.versions.toml"
WORKSPACE_CATALOG = (
    REPOSITORY_ROOT
    / "cli"
    / "src"
    / "coding_study"
    / "adapters"
    / "workspace_template"
    / "jvm"
    / "gradle"
    / "libs.versions.toml"
)


def kotlin_version(catalog: Path) -> str:
    return tomllib.loads(catalog.read_text(encoding="utf-8"))["versions"]["kotlin"]


def test_the_plugins_compile_against_the_workspaces_kotlin():
    assert kotlin_version(RUNNERS_CATALOG) == kotlin_version(WORKSPACE_CATALOG)
