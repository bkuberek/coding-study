"""`cstudy start --restore <path>`: one starter file, or one generated test file of an open level,
back to what `cstudy` provides (docs/specs/cli.md#cstudy-start)."""

import re
from dataclasses import replace

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_manifest import ProjectManifests
from coding_study.application.project_start import (
    RestoredFile,
    RestoreRequest,
    restore_project_file,
)
from coding_study.application.project_status import project_status
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.file_states import FileState
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import FileOrigin, content_digest
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS
from tests.project_fakes import PROJECT_FOLDER, PROJECT_SLUG
from tests.project_locks import PROJECT_LOCK, LockProbe, passing_environment

ENTRY = "bank/bank.py"
LEVEL_1_TESTS = "tests/test_level_1.py"
STARTER_ENTRY = (PROJECT_PROBLEMS / "0001-bank-project-python" / "starter" / ENTRY).read_text(
    encoding="utf-8"
)


@pytest.fixture
def environment(tmp_path) -> Environment:
    environment = passing_environment(repository_root(tmp_path, PROJECT_PROBLEMS))
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def restore(environment: Environment, path: str, **fields: object) -> RestoredFile:
    request = replace(RestoreRequest(PROJECT_SLUG, None, path), **fields)  # type: ignore[arg-type]
    return restore_project_file(environment, request)


def read(environment: Environment, path: str) -> str:
    return environment.workspace.read_text(f"{PROJECT_FOLDER}/{path}")


def write(environment: Environment, path: str, text: str) -> None:
    environment.workspace.write_text(f"{PROJECT_FOLDER}/{path}", text)


def state_of(environment: Environment, path: str) -> FileState:
    files = project_status(environment, None, None).files
    return next(file.state for file in files if file.path == path)


def test_restore_brings_back_a_modified_starter_file(environment):
    write(environment, ENTRY, "class Bank: pass\n")
    restore(environment, ENTRY)
    assert read(environment, ENTRY) == STARTER_ENTRY


def test_restore_brings_back_a_deleted_starter_file(environment):
    environment.workspace.absolute(f"{PROJECT_FOLDER}/{ENTRY}").unlink()
    restore(environment, ENTRY)
    assert read(environment, ENTRY) == STARTER_ENTRY


def test_restore_brings_back_an_edited_generated_test_file(environment):
    generated = read(environment, LEVEL_1_TESTS)
    write(environment, LEVEL_1_TESTS, "# mine\n")
    restore(environment, LEVEL_1_TESTS)
    assert read(environment, LEVEL_1_TESTS) == generated


def test_a_restored_file_is_unchanged_in_status(environment):
    write(environment, ENTRY, "class Bank: pass\n")
    restore(environment, ENTRY)
    assert state_of(environment, ENTRY) is FileState.UNCHANGED


def test_restore_reports_a_starter_file(environment):
    assert restore(environment, ENTRY) == RestoredFile(
        environment.problems.load(PROJECT_SLUG).meta, ENTRY, FileOrigin.STARTER, None
    )


def test_restore_reports_a_generated_test_files_level(environment):
    restored = restore(environment, LEVEL_1_TESTS)
    assert (restored.origin, restored.level) == (FileOrigin.LEVEL, 1)


def test_restore_records_what_it_wrote_in_the_manifest(environment):
    manifests = ProjectManifests(environment.workspace)
    original = manifests.recorded(PROJECT_SLUG, ENTRY)
    assert original is not None
    manifests.record(PROJECT_SLUG, replace(original, digest="from an older starter"))
    restore(environment, ENTRY)
    assert manifests.recorded(PROJECT_SLUG, ENTRY) == original


def test_restore_without_a_manifest_keeps_every_other_file_recorded(environment):
    environment.workspace.absolute(f".cs/projects/{PROJECT_SLUG}.json").unlink()
    restore(environment, ENTRY)
    manifest = ProjectManifests(environment.workspace).load(PROJECT_SLUG)
    assert manifest is not None
    assert [file.path for file in manifest.files] == [
        "README.md",
        ENTRY,
        "pyproject.toml",
        LEVEL_1_TESTS,
    ]


def test_restore_normalizes_the_path(environment):
    write(environment, ENTRY, "class Bank: pass\n")
    assert restore(environment, "./bank/../bank/bank.py").path == ENTRY


def test_restore_writes_under_the_projects_lock(environment):
    probe = LockProbe(environment.workspace.absolute(PROJECT_LOCK))
    probed = replace(
        environment, toolchains=FakeToolchains(project_test_generators={Language.PYTHON: probe})
    )
    restore(probed, LEVEL_1_TESTS)
    assert probe.held == [True]


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("../other/bank.py", "cannot restore ../other/bank.py: leaves the folder"),
        ("/etc/hosts", "cannot restore /etc/hosts: is absolute"),
        ("bank/ledger.py", "cannot restore bank/ledger.py: not a starter file or a generated"),
        ("tests/test_level_2.py", "cannot restore tests/test_level_2.py: not a starter file"),
    ],
)
def test_restore_refuses_a_file_cstudy_did_not_provide(environment, path, message):
    write(environment, "bank/ledger.py", "LEDGER = []\n")
    with pytest.raises(UsageError, match=re.escape(message)):
        restore(environment, path)


def test_restore_refuses_to_write_through_a_link(environment):
    environment.workspace.write_text("elsewhere/bank.py", "kept\n")
    environment.workspace.remove_folder(f"{PROJECT_FOLDER}/bank")
    environment.workspace.absolute(f"{PROJECT_FOLDER}/bank").symlink_to(
        "../../elsewhere", target_is_directory=True
    )
    with pytest.raises(UsageError, match=r"cannot restore bank/bank\.py: bank is a symbolic link"):
        restore(environment, ENTRY)


def test_restore_never_writes_through_a_link(environment):
    environment.workspace.write_text("elsewhere/bank.py", "kept\n")
    environment.workspace.remove_folder(f"{PROJECT_FOLDER}/bank")
    environment.workspace.absolute(f"{PROJECT_FOLDER}/bank").symlink_to(
        "../../elsewhere", target_is_directory=True
    )
    with pytest.raises(UsageError):
        restore(environment, ENTRY)
    assert environment.workspace.read_text("elsewhere/bank.py") == "kept\n"


def test_restore_refuses_a_missing_folder(environment):
    environment.workspace.remove_folder(PROJECT_FOLDER)
    with pytest.raises(
        UsageError, match=f"{PROJECT_FOLDER} is missing: cstudy start {PROJECT_SLUG}"
    ):
        restore(environment, ENTRY)


def test_restore_refuses_a_file_the_starter_no_longer_has(environment):
    environment.workspace.absolute(f"problems/0001-bank-project-python/starter/{ENTRY}").unlink()
    with pytest.raises(UsageError, match="the starter of bank-project-python no longer has it"):
        restore(environment, ENTRY)


def test_restore_needs_an_attempt_in_progress(tmp_path):
    environment = passing_environment(repository_root(tmp_path, PROJECT_PROBLEMS))
    with pytest.raises(UsageError, match="no attempt in progress"):
        restore(environment, ENTRY)


def test_restore_refuses_another_language(environment):
    with pytest.raises(UsageError, match="solved in python only"):
        restore(environment, ENTRY, language=Language.TYPESCRIPT)


def test_restore_is_for_project_problems(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    with pytest.raises(UsageError, match="--restore is for project problems"):
        restore_project_file(environment, RestoreRequest("two-sum", None, "two_sum.py"))


def test_restore_writes_the_exact_generated_text(environment):
    write(environment, LEVEL_1_TESTS, "# mine\n")
    restore(environment, LEVEL_1_TESTS)
    recorded = ProjectManifests(environment.workspace).recorded(PROJECT_SLUG, LEVEL_1_TESTS)
    assert recorded is not None
    assert recorded.digest == content_digest(read(environment, LEVEL_1_TESTS))
