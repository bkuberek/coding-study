"""Static checks S14 to S16 on Rust project problems: the crate, its `Cargo.toml` and its
`.cargo/config.toml` (docs/specs/problem-format.md#rust-projects)."""

from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.project import Project, ProjectFile, ProjectFiles, ProjectTree
from coding_study.domain.signature import ClassSignature, Param
from coding_study.domain.static_checks import ProblemContent, static_checks
from coding_study.domain.type_dsl import parse_value_type
from tests.fakes import repository_root
from tests.helpers import RUST_BANK_PROJECT, RUST_PROJECT_PROBLEMS

FIXTURE = RUST_PROJECT_PROBLEMS / RUST_BANK_PROJECT
DIRECTORY = f"problems/{RUST_BANK_PROJECT}"
META = f"{DIRECTORY}/meta.yaml"
STARTER = f"{DIRECTORY}/starter"
CARGO = f"{STARTER}/Cargo.toml"
CONFIG = f"{STARTER}/.cargo/config.toml"
MANIFEST = """\
[package]
name = "bank"
version = "0.1.0"
edition = "2021"
rust-version = "1.80"
publish = false
"""
DECIMAL = 'rust_decimal = { version = "=1.43.0", default-features = false, features = ["maths"] }'
CHRONO = 'chrono = { version = "=0.4.45", default-features = false, features = ["std"] }'


@pytest.fixture(scope="module")
def bank(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), RUST_PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-rust")


def content(problem) -> ProblemContent:
    return ProblemContent(
        directory=DIRECTORY,
        problem=problem,
        problem_markdown=(FIXTURE / "problem.md").read_text(),
        explanation=(FIXTURE / "solutions" / "explanation.md").read_text(),
        files=("meta.yaml", "problem.md", "tests.json"),
        solution_files=("explanation.md",),
    )


def errors(problem) -> list[str]:
    return [str(issue) for issue in static_checks(content(problem)).errors]


def errors_on(problem, prefix: str) -> list[str]:
    return [issue for issue in errors(problem) if issue.startswith(prefix)]


def with_meta(problem, **changes):
    return replace(problem, meta=replace(problem.meta, **changes))


def text_file(path: str, text: str = "") -> ProjectFile:
    return ProjectFile(path, len(text.encode()), text)


def project_files(problem) -> ProjectFiles:
    assert problem.project_files is not None
    return problem.project_files


def with_starter(problem, *files: ProjectFile):
    """The starter with `files` added, or replacing the files at their paths."""
    starter = project_files(problem).starter
    assert starter is not None
    paths = {file.path for file in files}
    kept = tuple(file for file in starter.files if file.path not in paths)
    tree = ProjectTree(tuple(sorted((*kept, *files), key=lambda file: file.path)))
    return replace(problem, project_files=replace(project_files(problem), starter=tree))


def without_starter_files(problem, *paths: str):
    starter = project_files(problem).starter
    assert starter is not None
    kept = tuple(file for file in starter.files if file.path not in paths)
    return replace(
        problem, project_files=replace(project_files(problem), starter=ProjectTree(kept))
    )


def with_manifest(problem, text: str):
    return with_starter(problem, text_file("Cargo.toml", text))


def with_constructor_param(problem, type_text: str):
    signature = problem.meta.signature
    assert isinstance(signature, ClassSignature)
    params = (Param("seed", parse_value_type(type_text)),)
    return with_meta(problem, signature=replace(signature, constructor_params=params))


def test_the_rust_fixture_passes(bank):
    assert errors(bank) == []


def test_the_rust_fixture_has_no_warnings(bank):
    assert static_checks(content(bank)).warnings == ()


# S14


def test_a_rust_entry_is_a_crate_name(bank):
    problem = with_meta(bank, project=Project("src/lib.rs"))
    assert errors(problem) == [
        f'{META}: project.entry: "src/lib.rs" is not a crate name such as bank: lowercase '
        "letters, digits and _"
    ]


def test_rust_level_tests_go_to_tests(bank):
    problem = with_meta(bank, project=Project("bank", "checks"))
    assert errors(problem) == [
        f'{META}: project.tests: "checks" is not tests, where Cargo finds integration tests'
    ]


@pytest.mark.parametrize("type_text", ["long", "string[]", "list<list<char>>", "double"])
def test_a_rust_project_signature_takes_scalars_arrays_and_lists(bank, type_text):
    assert errors_on(with_constructor_param(bank, type_text), f"{META}: signature") == []


# S15: the crate


def test_a_rust_starter_holds_the_library_root(bank):
    problem = without_starter_files(bank, "src/lib.rs")
    assert errors(problem) == [f"{STARTER}: has no src/lib.rs for the entry bank"]


def test_a_rust_starter_has_a_manifest(bank):
    assert errors(without_starter_files(bank, "Cargo.toml")) == [f"{CARGO}: missing"]


def test_a_rust_manifest_is_valid_toml(bank):
    issues = errors(with_manifest(bank, "[package\n"))
    assert len(issues) == 1
    assert issues[0].startswith(f"{CARGO}: is not valid TOML: ")


def test_a_rust_manifest_has_a_package(bank):
    assert errors(with_manifest(bank, "")) == [f"{CARGO}: has no [package] table"]


def test_a_rust_manifest_names_the_entry_crate(bank):
    problem = with_manifest(bank, MANIFEST.replace('"bank"', '"bank_app"'))
    assert errors(problem) == [f'{CARGO}: names the crate "bank_app", not the entry bank']


@pytest.mark.parametrize(
    ("line", "issue"),
    [
        ('edition = "2021"\n', 'needs edition = "2021"'),
        ('edition = "2018"', 'needs edition = "2021"'),
        ('rust-version = "1.80"\n', 'needs rust-version = "1.80"'),
        ('rust-version = "1.85"', 'needs rust-version = "1.80"'),
    ],
    ids=["no edition", "another edition", "no rust-version", "another rust-version"],
)
def test_a_rust_manifest_pins_the_edition_and_the_oldest_rust(bank, line, issue):
    old = 'edition = "2021"' if "edition" in line else 'rust-version = "1.80"'
    text = MANIFEST.replace(f"{old}\n", "" if line.endswith("\n") else f"{line}\n")
    assert errors(with_manifest(bank, text)) == [f"{CARGO}: {issue}"]


@pytest.mark.parametrize("key", ["build", "links", "workspace"])
def test_a_rust_package_has_no_build_script_links_or_workspace(bank, key):
    problem = with_manifest(bank, f'{MANIFEST}{key} = "x"\n')
    assert errors(problem) == [f"{CARGO}: [package] sets {key}"]


@pytest.mark.parametrize(
    ("table", "name"),
    [
        ("[workspace]\n", "workspace"),
        ("[profile.dev]\nopt-level = 3\n", "profile"),
        ('[[bin]]\nname = "x"\npath = "src/main.rs"\n', "bin"),
        ('[lib]\npath = "src/root.rs"\n', "lib"),
        ('[patch.crates-io]\nchrono = { path = "x" }\n', "patch"),
        ('[build-dependencies]\nchrono = "1"\n', "build-dependencies"),
    ],
    ids=["workspace", "profile", "bin", "lib", "patch", "build-dependencies"],
)
def test_a_rust_manifest_has_only_the_package_and_its_dependencies(bank, table, name):
    problem = with_manifest(bank, f"{MANIFEST}\n{table}")
    assert errors(problem) == [
        f"{CARGO}: has a [{name}] table: a project crate has only [package], [dependencies] "
        "and [dev-dependencies]"
    ]


@pytest.mark.parametrize("table", ["dependencies", "dev-dependencies"])
def test_a_rust_manifest_may_depend_on_the_vendored_crates(bank, table):
    problem = with_manifest(bank, f"{MANIFEST}\n[{table}]\n{DECIMAL}\n{CHRONO}\n")
    assert errors(problem) == []


@pytest.mark.parametrize("table", ["dependencies", "dev-dependencies"])
def test_a_rust_manifest_lists_no_other_crate(bank, table):
    problem = with_manifest(bank, f'{MANIFEST}\n[{table}]\nserde = "1"\n')
    assert errors(problem) == [
        f"{CARGO}: [{table}] lists serde: a project crate may use only the vendored "
        "rust_decimal and chrono"
    ]


def test_a_rust_manifest_declares_a_vendored_crate_as_the_runner_does(bank):
    problem = with_manifest(bank, f'{MANIFEST}\n[dependencies]\nchrono = "0.4"\n')
    assert errors(problem) == [
        f"{CARGO}: [dependencies] declares chrono otherwise than the runner: {CHRONO}"
    ]


@pytest.mark.parametrize(
    ("type_text", "crate"), [("decimal", "rust_decimal"), ("list<date>", "chrono")]
)
def test_a_signature_with_a_vendored_type_needs_its_crate(bank, type_text, crate):
    problem = with_constructor_param(bank, type_text)
    assert errors_on(problem, CARGO) == [
        f"{CARGO}: the signature uses {type_text.removeprefix('list<').removesuffix('>')}: "
        f"[dependencies] needs {crate}"
    ]


def test_a_signature_with_a_vendored_type_is_fine_with_its_crate(bank):
    problem = with_manifest(
        with_constructor_param(bank, "decimal"), f"{MANIFEST}\n[dependencies]\n{DECIMAL}\n"
    )
    assert errors_on(problem, CARGO) == []


# S15: the vendored source


def test_a_rust_starter_has_a_cargo_config(bank):
    assert errors(without_starter_files(bank, ".cargo/config.toml")) == [f"{CONFIG}: missing"]


def test_a_rust_cargo_config_may_have_comments_and_other_spacing(bank):
    text = (
        "# crates.io from the runtime\n[source.crates-io]\nreplace-with = 'cstudy-vendor'\n"
        "[source.cstudy-vendor]\ndirectory = '../../.cs/runtime/runners/rust/vendor'\n"
    )
    assert errors(with_starter(bank, text_file(".cargo/config.toml", text))) == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[source.crates-io]\nreplace-with = 'cstudy-vendor'\n",
        "[source.crates-io]\nreplace-with = 'cstudy-vendor'\n[source.cstudy-vendor]\n"
        "directory = '/opt/vendor'\n",
        "[build]\nrustflags = ['-O']\n[source.crates-io]\nreplace-with = 'cstudy-vendor'\n"
        "[source.cstudy-vendor]\ndirectory = '../../.cs/runtime/runners/rust/vendor'\n",
        "[source",
    ],
    ids=["empty", "no directory", "another directory", "more settings", "not toml"],
)
def test_a_rust_cargo_config_holds_exactly_the_vendored_source(bank, text):
    problem = with_starter(bank, text_file(".cargo/config.toml", text))
    assert errors(problem) == [
        f"{CONFIG}: does not hold exactly the vendored source of "
        "docs/specs/problem-format.md#rust-projects"
    ]


# S15: what a crate never ships


def test_a_rust_starter_holds_no_cargo_lock(bank):
    problem = with_starter(bank, text_file("Cargo.lock", "version = 3\n"))
    assert errors(problem) == [f"{STARTER}/Cargo.lock: is a lock file"]


def test_a_rust_starter_holds_no_target_directory(bank):
    problem = with_starter(bank, text_file("target/debug/.fingerprint/x", "x"))
    assert errors(problem) == [f"{STARTER}/target: is build output or a cache"]


@pytest.mark.parametrize("path", ["build.rs", "rust-toolchain", "rust-toolchain.toml"])
def test_a_rust_starter_has_no_build_script_or_toolchain_file(bank, path):
    problem = with_starter(bank, text_file(path, "x"))
    assert errors(problem) == [
        f"{STARTER}/{path}: a project crate has no build script and uses the workspace's toolchain"
    ]


# S16


def test_no_rust_starter_file_has_a_generated_test_name(bank):
    problem = with_starter(bank, text_file("tests/level_1.rs", "#[test]\nfn ok() {}\n"))
    assert errors(problem) == [f"{STARTER}/tests/level_1.rs: has the name of a generated test file"]


def test_a_rust_starter_may_ship_its_own_tests(bank):
    problem = with_starter(bank, text_file("tests/ledger.rs", "#[test]\nfn ok() {}\n"))
    assert errors(problem) == []
