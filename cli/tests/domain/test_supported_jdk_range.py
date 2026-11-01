"""The supported JDK range is defined twice, in `domain/jdk.py` and in the runners' Gradle version
catalog, since neither side can read the other without a file read in the domain or a generator
across languages. These tests keep the two equal (docs/decisions/0016-jdk-range.md)."""

import tomllib

import pytest

from coding_study.domain.jdk import SUPPORTED_JDKS
from tests.helpers import REPOSITORY_ROOT

VERSION_CATALOG = REPOSITORY_ROOT / "runners" / "jvm" / "gradle" / "libs.versions.toml"


@pytest.fixture(scope="module")
def versions() -> dict[str, str]:
    return tomllib.loads(VERSION_CATALOG.read_text(encoding="utf-8"))["versions"]


def test_gradle_and_python_agree_on_the_oldest_supported_jdk(versions):
    assert int(versions["jdk-minimum"]) == SUPPORTED_JDKS.minimum


def test_gradle_and_python_agree_on_the_newest_supported_jdk(versions):
    assert int(versions["jdk-maximum"]) == SUPPORTED_JDKS.maximum
