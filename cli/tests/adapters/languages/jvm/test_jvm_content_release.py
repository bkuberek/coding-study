"""What cstudy builds from the content compiles at the problem's minimum release, `cs.release`;
the user's own files compile at the selected JDK's level, with no `cs.release`
(docs/specs/runners.md#the-jdk-and-the-release-level)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.jvm.runner import JvmRunner
from coding_study.application.ports import (
    BenchCode,
    BuildScope,
    ProjectGrading,
    ProjectScope,
    ProjectSuite,
    References,
    UserCode,
)
from coding_study.domain.jdk import DeclaredJdk
from coding_study.domain.problem import Language
from tests.adapters.languages.jvm.fake_gradle import (
    FakeGradle,
    ProjectGradle,
    jvm_context,
    reference_sources,
)
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
NEEDS_24 = replace(TWO_SUM, jdk=DeclaredJdk(minimum=24))
RELEASE = "-Pcs.release="


def releases(builds) -> list[list[str]]:
    """The `cs.release` arguments of each build."""
    return [[arg for arg in build if arg.startswith(RELEASE)] for build in builds]


def prepare(root: Path, gradle: FakeGradle, language: Language, scope: BuildScope):
    return JvmRunner(jvm_context(root), language, gradle).prepare(scope, [].append)


@pytest.fixture(params=[Language.JAVA, Language.KOTLIN], ids=str)
def language(request: pytest.FixtureRequest) -> Language:
    return request.param


def test_references_compile_at_the_supported_minimum_without_a_declared_one(
    root, tmp_path, language
):
    gradle = FakeGradle(root)
    sources = reference_sources(tmp_path / "solutions", language, "hash-map")
    prepare(root, gradle, language, References(TWO_SUM, sources))
    assert releases(gradle.builds) == [[f"{RELEASE}21"]]


def test_references_compile_at_the_declared_minimum(root, tmp_path, language):
    gradle = FakeGradle(root)
    sources = reference_sources(tmp_path / "solutions", language, "hash-map")
    prepare(root, gradle, language, References(NEEDS_24, sources))
    assert releases(gradle.builds) == [[f"{RELEASE}24"]]


def test_the_users_file_compiles_at_the_jdks_level(root, language):
    gradle = FakeGradle(root)
    prepare(root, gradle, language, UserCode(NEEDS_24))
    assert releases(gradle.builds) == [[]]


def test_a_bench_compiles_the_references_at_the_minimum_and_the_users_file_at_the_jdks_level(
    root, tmp_path, language
):
    gradle = FakeGradle(root)
    sources = reference_sources(tmp_path / "solutions", language, "hash-map")
    prepare(root, gradle, language, BenchCode(NEEDS_24, sources))
    assert releases(gradle.builds) == [[f"{RELEASE}24"], []]


def test_a_references_only_bench_builds_no_user_file(root, tmp_path, language):
    gradle = FakeGradle(root)
    sources = reference_sources(tmp_path / "solutions", language, "hash-map")
    prepare(root, gradle, language, BenchCode(NEEDS_24, sources, references_only=True))
    assert releases(gradle.builds) == [[f"{RELEASE}24"]]


# project folders


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    project = tmp_path / "projects" / "bank-project"
    project.mkdir(parents=True)
    return project


def prepare_project(tmp_path: Path, language: Language, scope: ProjectScope) -> ProjectGradle:
    gradle = ProjectGradle()
    runner = JvmRunner(jvm_context(tmp_path), language, gradle)
    runner.prepare_project(scope, [].append)
    return gradle


@pytest.mark.parametrize("scope_of", [ProjectSuite, ProjectGrading], ids=["suite", "grading"])
def test_a_reference_project_compiles_at_the_given_release(tmp_path, folder, language, scope_of):
    gradle = prepare_project(tmp_path, language, scope_of(folder, release=24))
    assert releases(gradle.builds) == [[f"{RELEASE}24"]]


@pytest.mark.parametrize("scope_of", [ProjectSuite, ProjectGrading], ids=["suite", "grading"])
def test_the_users_project_compiles_at_the_jdks_level(tmp_path, folder, language, scope_of):
    gradle = prepare_project(tmp_path, language, scope_of(folder))
    assert releases(gradle.builds) == [[]]


def test_the_release_comes_before_the_excluded_test_files(tmp_path, folder):
    scope = ProjectSuite(folder, exclude=("src/test/java/bank/Level2Test.java",), release=21)
    gradle = prepare_project(tmp_path, Language.JAVA, scope)
    assert gradle.builds[0][-2:] == (
        f"{RELEASE}21",
        "-Pcs.exclude=src/test/java/bank/Level2Test.java",
    )
