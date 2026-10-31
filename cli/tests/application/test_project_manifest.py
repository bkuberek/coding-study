"""The starter manifest of a project folder: what `cstudy start` and `cstudy submit` provided, kept
in `.cs/projects/<slug>.json` (docs/specs/installation-and-workspaces.md#project-folders)."""

import json
from dataclasses import replace

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_manifest import ProjectManifests, provided_now
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.project_manifest import (
    FileOrigin,
    ProjectManifest,
    ProvidedFile,
    content_digest,
)
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    FakeTestGenerator,
    ScriptedProjectProcess,
    expected_answers,
    project_environment,
)

MANIFEST = f".cs/projects/{PROJECT_SLUG}.json"
STARTER = ("README.md", "bank/bank.py", "pyproject.toml")
LEVEL_1_TESTS = "tests/test_level_1.py"
LEVEL_2_TESTS = "tests/test_level_2.py"
README = ProvidedFile("README.md", content_digest("# Bank\n"), FileOrigin.STARTER)


@pytest.fixture
def environment(tmp_path) -> Environment:
    process = ScriptedProjectProcess()
    environment = project_environment(tmp_path, process)
    process.answer = expected_answers(environment.problems.load(PROJECT_SLUG))
    return environment


@pytest.fixture
def manifests(environment) -> ProjectManifests:
    return ProjectManifests(environment.workspace)


def start(environment: Environment, fresh: bool = False) -> None:
    start_attempt(environment, StartRequest(PROJECT_SLUG, fresh=fresh))


def recorded(manifests: ProjectManifests) -> ProjectManifest:
    manifest = manifests.load(PROJECT_SLUG)
    assert manifest is not None
    return manifest


def digest_of(environment: Environment, path: str) -> str:
    return content_digest(environment.workspace.read_text(f"{PROJECT_FOLDER}/{path}"))


def test_a_saved_manifest_loads_back(manifests):
    manifest = ProjectManifest((README,))
    manifests.save(PROJECT_SLUG, manifest)
    assert manifests.load(PROJECT_SLUG) == manifest


def test_the_manifest_is_a_sorted_json_document_by_path(manifests, environment):
    level = ProvidedFile(LEVEL_1_TESTS, "ccc", FileOrigin.LEVEL, 1)
    manifests.save(PROJECT_SLUG, ProjectManifest((README, level)))
    assert json.loads(environment.workspace.read_text(MANIFEST)) == {
        "format": 1,
        "files": {
            "README.md": {"origin": "starter", "sha256": README.digest},
            LEVEL_1_TESTS: {"origin": "level", "level": 1, "sha256": "ccc"},
        },
    }


def test_a_missing_manifest_loads_as_none(manifests):
    assert manifests.load(PROJECT_SLUG) is None


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"format": 2, "files": {}}',
        '{"format": 1, "files": []}',
        '{"format": 1, "files": {"README.md": {"origin": "mine", "sha256": "a"}}}',
        '{"format": 1, "files": {"README.md": {"origin": "starter"}}}',
        '{"format": 1, "files": {"../README.md": {"origin": "starter", "sha256": "a"}}}',
        '{"format": 1, "files": {"t.py": {"origin": "level", "level": "1", "sha256": "a"}}}',
    ],
)
def test_an_unreadable_manifest_loads_as_none(manifests, environment, text):
    environment.workspace.write_text(MANIFEST, text)
    assert manifests.load(PROJECT_SLUG) is None


def test_record_replaces_the_file_of_its_path(manifests):
    manifests.save(PROJECT_SLUG, ProjectManifest((README,)))
    changed = replace(README, digest="ddd")
    manifests.record(PROJECT_SLUG, changed)
    assert recorded(manifests).files == (changed,)


def test_record_starts_a_missing_manifest(manifests):
    manifests.record(PROJECT_SLUG, README)
    assert recorded(manifests).files == (README,)


def test_recorded_finds_the_file_of_a_path(manifests):
    manifests.save(PROJECT_SLUG, ProjectManifest((README,)))
    assert manifests.recorded(PROJECT_SLUG, "README.md") == README


def test_recorded_of_an_unrecorded_path_is_none(manifests):
    manifests.save(PROJECT_SLUG, ProjectManifest((README,)))
    assert manifests.recorded(PROJECT_SLUG, LEVEL_1_TESTS) is None


def test_recorded_without_a_manifest_is_none(manifests):
    assert manifests.recorded(PROJECT_SLUG, "README.md") is None


def test_provided_now_holds_the_starter_and_each_open_levels_generated_file(environment):
    problem = environment.problems.load(PROJECT_SLUG)
    manifest = provided_now(problem, FakeTestGenerator(), 2)
    assert [(file.path, file.origin, file.level) for file in manifest.files] == [
        ("README.md", FileOrigin.STARTER, None),
        ("bank/bank.py", FileOrigin.STARTER, None),
        ("pyproject.toml", FileOrigin.STARTER, None),
        (LEVEL_1_TESTS, FileOrigin.LEVEL, 1),
        (LEVEL_2_TESTS, FileOrigin.LEVEL, 2),
    ]


# what cstudy start and cstudy submit record


def test_a_new_attempt_records_each_starter_file_as_copied(environment, manifests):
    start(environment)
    manifest = recorded(manifests)
    assert [manifest.file(path) for path in STARTER] == [
        ProvidedFile(path, digest_of(environment, path), FileOrigin.STARTER) for path in STARTER
    ]


def test_a_new_attempt_records_level_1s_test_file(environment, manifests):
    start(environment)
    assert recorded(manifests).file(LEVEL_1_TESTS) == ProvidedFile(
        LEVEL_1_TESTS, digest_of(environment, LEVEL_1_TESTS), FileOrigin.LEVEL, 1
    )


def test_the_starters_content_is_recorded_even_over_a_file_it_did_not_copy(environment, manifests):
    environment.workspace.write_text(f"{PROJECT_FOLDER}/README.md", "# mine\n")
    start(environment)
    assert recorded(manifests).file("README.md") != ProvidedFile(
        "README.md", content_digest("# mine\n"), FileOrigin.STARTER
    )


def test_an_unlock_records_the_opened_levels_test_file(environment, manifests):
    start(environment)
    submit_project(environment, SubmitRequest(), [].append)
    assert recorded(manifests).file(LEVEL_2_TESTS) == ProvidedFile(
        LEVEL_2_TESTS, digest_of(environment, LEVEL_2_TESTS), FileOrigin.LEVEL, 2
    )


def test_an_unlock_records_what_it_generated_over_a_file_you_wrote_first(environment, manifests):
    start(environment)
    environment.workspace.write_text(f"{PROJECT_FOLDER}/{LEVEL_2_TESTS}", "# mine\n")
    submit_project(environment, SubmitRequest(), [].append)
    provided = recorded(manifests).file(LEVEL_2_TESTS)
    assert provided is not None
    assert provided.digest != content_digest("# mine\n")


def test_a_resumed_attempt_keeps_the_recorded_digests(environment, manifests):
    start(environment)
    manifests.record(PROJECT_SLUG, replace(README, digest="from an older starter"))
    start(environment)
    assert recorded(manifests).file("README.md") == replace(README, digest="from an older starter")


def test_a_resumed_attempt_records_a_test_file_it_writes_back(environment, manifests):
    start(environment)
    manifests.record(PROJECT_SLUG, ProvidedFile(LEVEL_1_TESTS, "older", FileOrigin.LEVEL, 1))
    environment.workspace.absolute(f"{PROJECT_FOLDER}/{LEVEL_1_TESTS}").unlink()
    start(environment)
    assert recorded(manifests).file(LEVEL_1_TESTS) == ProvidedFile(
        LEVEL_1_TESTS, digest_of(environment, LEVEL_1_TESTS), FileOrigin.LEVEL, 1
    )


def test_a_resumed_attempt_rebuilds_a_missing_manifest(environment, manifests):
    start(environment)
    before = recorded(manifests)
    environment.workspace.absolute(MANIFEST).unlink()
    start(environment)
    assert recorded(manifests) == before


def test_a_resumed_attempt_rebuilds_the_manifest_of_a_folder_copied_again(environment, manifests):
    start(environment)
    manifests.record(PROJECT_SLUG, ProvidedFile("bank/ledger.py", "gone", FileOrigin.STARTER))
    environment.workspace.remove_folder(PROJECT_FOLDER)
    start(environment)
    assert recorded(manifests).file("bank/ledger.py") is None


def test_fresh_replaces_the_manifest(environment, manifests):
    start(environment)
    submit_project(environment, SubmitRequest(), [].append)
    start(environment, fresh=True)
    assert recorded(manifests).file(LEVEL_2_TESTS) is None
