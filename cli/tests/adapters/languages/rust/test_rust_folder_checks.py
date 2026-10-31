"""The Rust rows of `cstudy doctor`
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace)."""

import json

import pytest

from coding_study.adapters.languages.rust.folder_checks import (
    CONFIG_CHECK,
    IDE_COMMAND,
    LINKED_CHECK,
    RustFolderChecks,
)
from coding_study.adapters.languages.rust.runner import RustRunner
from coding_study.application.ports import ProjectFolderChecks
from coding_study.domain.workspace_projects import RUST_CARGO_CONFIG

BANK = "projects/bank-project-rust"
LEDGER = "projects/ledger-project-rust"


@pytest.fixture
def root(tmp_path):
    (tmp_path / ".cs/runtime/runners/rust/vendor").mkdir(parents=True)
    return tmp_path


def rust_folder(root, folder: str, config: str | None = RUST_CARGO_CONFIG) -> None:
    (root / folder).mkdir(parents=True)
    (root / folder / "Cargo.toml").write_text('[package]\nname = "bank"\n')
    if config is not None:
        (root / folder / ".cargo").mkdir()
        (root / folder / ".cargo/config.toml").write_text(config)


def link(root, *manifests: str) -> None:
    (root / ".vscode").mkdir(exist_ok=True)
    settings = {"rust-analyzer.linkedProjects": ["rust/Cargo.toml", *manifests]}
    (root / ".vscode/settings.json").write_text(json.dumps(settings))


def failing(root, name: str) -> tuple[str, ...]:
    (check,) = (check for check in RustFolderChecks(root).folder_checks() if check.name == name)
    return check.failing


def test_the_rust_runner_checks_its_project_folders():
    assert issubclass(RustRunner, ProjectFolderChecks)


def test_a_folder_whose_config_reaches_the_vendored_crates_passes(root):
    rust_folder(root, BANK)
    assert failing(root, CONFIG_CHECK) == ()


def test_a_folder_without_a_config_fails(root):
    rust_folder(root, BANK, config=None)
    assert failing(root, CONFIG_CHECK) == (BANK,)


def test_a_config_naming_a_missing_directory_fails(root):
    rust_folder(root, BANK, RUST_CARGO_CONFIG.replace("vendor", "elsewhere"))
    assert failing(root, CONFIG_CHECK) == (BANK,)


def test_a_config_that_replaces_nothing_fails(root):
    rust_folder(root, BANK, "[build]\njobs = 2\n")
    assert failing(root, CONFIG_CHECK) == (BANK,)


def test_a_config_that_is_not_toml_fails(root):
    rust_folder(root, BANK, "[source.crates-io\n")
    assert failing(root, CONFIG_CHECK) == (BANK,)


def test_folders_without_a_cargo_manifest_are_not_checked(root):
    (root / "projects/bank-project-python").mkdir(parents=True)
    assert failing(root, CONFIG_CHECK) == ()


def test_failing_folders_come_in_path_order(root):
    rust_folder(root, LEDGER, config=None)
    rust_folder(root, BANK, config=None)
    assert failing(root, CONFIG_CHECK) == (BANK, LEDGER)


def test_without_vscode_settings_there_is_no_linked_projects_row(root):
    rust_folder(root, BANK)
    names = [check.name for check in RustFolderChecks(root).folder_checks()]
    assert names == [CONFIG_CHECK]


def test_a_linked_folder_passes(root):
    rust_folder(root, BANK)
    link(root, f"{BANK}/Cargo.toml")
    assert failing(root, LINKED_CHECK) == ()


def test_an_unlinked_folder_fails(root):
    rust_folder(root, BANK)
    rust_folder(root, LEDGER)
    link(root, f"{BANK}/Cargo.toml")
    assert failing(root, LINKED_CHECK) == (LEDGER,)


def test_settings_that_are_not_json_link_nothing(root):
    rust_folder(root, BANK)
    (root / ".vscode").mkdir()
    (root / ".vscode/settings.json").write_text("{ // a comment\n}")
    assert failing(root, LINKED_CHECK) == (BANK,)


def test_unlinked_folders_are_fixed_by_the_ide_command(root):
    link(root)
    (check,) = (c for c in RustFolderChecks(root).folder_checks() if c.name == LINKED_CHECK)
    assert check.fix == IDE_COMMAND


def test_a_repair_writes_each_missing_config(root):
    rust_folder(root, BANK, config=None)
    assert RustFolderChecks(root).repair_folders() == (f"{BANK}/.cargo/config.toml",)
    assert (root / BANK / ".cargo/config.toml").read_text() == RUST_CARGO_CONFIG


def test_a_repaired_folder_passes(root):
    rust_folder(root, BANK, config=None)
    RustFolderChecks(root).repair_folders()
    assert failing(root, CONFIG_CHECK) == ()


def test_a_repair_keeps_a_config_naming_another_directory(root):
    other = RUST_CARGO_CONFIG.replace("vendor", "elsewhere")
    rust_folder(root, BANK, other)
    assert RustFolderChecks(root).repair_folders() == ()
    assert (root / BANK / ".cargo/config.toml").read_text() == other


def test_a_repair_leaves_a_cargo_file_that_is_not_a_directory(root):
    rust_folder(root, BANK, config=None)
    (root / BANK / ".cargo").write_text("")
    assert RustFolderChecks(root).repair_folders() == ()
