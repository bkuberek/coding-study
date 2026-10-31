"""A Rust project's build workspace (docs/specs/runners.md#rust-projects), with Cargo's JSON output
recorded from real builds of the fixture project (tests/.../rust/recorded/project-*.jsonl): the
workspace path is written `{root}`."""

import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.project_build import (
    ProjectBuildError,
    RustBuildSettings,
    RustProjectBuild,
    SuiteTarget,
)
from coding_study.adapters.languages.rust.toolchain import CargoOutcome
from coding_study.application.ports import BuildFailed
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.runs import UserError
from coding_study.domain.signature import ClassSignature
from tests.project_builders import BANK

RECORDED = Path(__file__).parent / "recorded"
HOST = "aarch64-apple-darwin"
SLUG = "bank-project-rust"
MANIFEST = '[package]\nname = "bank"\nedition = "2021"\n'
SIGNATURE: ClassSignature = BANK


@dataclass
class ReplayedCargo:
    """Answers each build with the next recorded output, after creating the binaries it names."""

    root: Path
    outputs: list[tuple[int, str, str]] = field(default_factory=list[tuple[int, str, str]])
    builds: list[tuple[list[str], Path, dict[str, str]]] = field(
        default_factory=list[tuple[list[str], Path, dict[str, str]]]
    )

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CargoOutcome:
        self.builds.append((list(arguments), cwd, dict(environment)))
        exit_code, name, stderr = self.outputs.pop(0)
        stdout = (RECORDED / f"{name}.jsonl").read_text().replace("{root}", str(self.root))
        for line in stdout.splitlines():
            binary = json.loads(line).get("executable")
            if binary:
                Path(binary).parent.mkdir(parents=True, exist_ok=True)
                Path(binary).write_text("binary")
        return CargoOutcome(exit_code, stdout, stderr.replace("{root}", str(self.root)))

    def host(self, cwd: Path) -> str:
        return HOST

    def release(self, cwd: Path) -> str:
        return "1.92.0"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = (tmp_path / "ws").resolve()
    folder = root / "projects" / SLUG
    folder.mkdir(parents=True)
    (folder / "Cargo.toml").write_text(MANIFEST)
    (root / ".cs/runtime/runners/rust").mkdir(parents=True)
    return root


def project_build(
    workspace: Path, *outputs: tuple[int, str, str]
) -> tuple[RustProjectBuild, ReplayedCargo]:
    cargo = ReplayedCargo(workspace, list(outputs))
    runtime = workspace / ".cs/runtime/runners/rust"
    settings = RustBuildSettings(workspace, runtime, cargo, lambda: HOST)
    return RustProjectBuild(settings, SLUG, workspace / "projects" / SLUG), cargo


def build_directory(workspace: Path) -> Path:
    return workspace / ".cs/build/rust-projects" / SLUG


def harness_manifest(workspace: Path) -> dict[str, object]:
    return tomllib.loads((build_directory(workspace) / "harness/Cargo.toml").read_text())


BUILT = (0, "project-harness", "")
SUITE = (101, "project-suite", 'error: could not compile `bank` (test "broken")\n')


# the build workspace


def test_the_build_workspace_has_the_harness_as_its_only_member(workspace):
    build, _ = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    manifest = tomllib.loads((build_directory(workspace) / "Cargo.toml").read_text())
    assert manifest["workspace"] == {"resolver": "2", "members": ["harness"]}


def test_the_harness_depends_on_the_project_crate_by_path_as_user(workspace):
    build, _ = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    dependencies = harness_manifest(workspace)["dependencies"]
    assert isinstance(dependencies, dict)
    assert dependencies["user"] == {"package": "bank", "path": f"../../../../../projects/{SLUG}"}


def test_the_harness_is_named_after_the_problem(workspace):
    build, _ = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    assert harness_manifest(workspace)["package"]["name"] == "project_bank_project_rust"  # type: ignore[index]


def test_the_crate_is_whatever_the_projects_manifest_names(workspace):
    (workspace / "projects" / SLUG / "Cargo.toml").write_text('[package]\nname = "ledger"\n')
    build, _ = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    assert harness_manifest(workspace)["dependencies"]["user"]["package"] == "ledger"  # type: ignore[index]


def test_a_build_uses_the_dev_profile_offline_for_the_host(workspace):
    build, cargo = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    ((arguments, _, _),) = cargo.builds
    assert arguments[:8] == [
        "--offline",
        "--profile",
        "dev",
        "--message-format=json",
        "--target",
        HOST,
        "-p",
        "project_bank_project_rust",
    ]


def test_a_build_pins_the_dev_profile_and_the_vendored_crates(workspace):
    build, cargo = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    ((arguments, _, _),) = cargo.builds
    assert "profile.dev.overflow-checks=true" in arguments
    assert 'source.crates-io.replace-with="cstudy-vendor"' in arguments


def test_a_build_shares_the_target_directory_and_has_a_cargo_home_of_its_own(workspace):
    build, cargo = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    ((_, cwd, environment),) = cargo.builds
    assert (cwd, environment) == (
        build_directory(workspace),
        {
            "CARGO_TARGET_DIR": str(workspace / ".cs/build/rust/target"),
            "CARGO_HOME": str(build_directory(workspace) / "cargo-home"),
        },
    )


def test_nothing_is_written_into_the_project_folder(workspace):
    build, _ = project_build(workspace, BUILT, SUITE)
    build.harness(SIGNATURE)
    build.tests(())
    assert [path.name for path in (workspace / "projects" / SLUG).iterdir()] == ["Cargo.toml"]


# grading


def test_the_harness_is_a_private_copy_of_the_built_binary(workspace):
    build, _ = project_build(workspace, BUILT)
    binary = build.harness(SIGNATURE)
    assert isinstance(binary, Path)
    assert binary.parent.parent == build_directory(workspace) / "run"
    assert binary.read_text() == "binary"


def test_the_bridge_calls_the_crate_through_its_root(workspace):
    build, _ = project_build(workspace, BUILT)
    build.harness(SIGNATURE)
    bridge = (build_directory(workspace) / "harness/main.rs").read_text()
    assert "let instance: user::Bank = user::Bank::new();" in bridge


def test_a_first_build_is_cold_and_a_later_one_warm(workspace):
    build, _ = project_build(workspace, BUILT)
    cold = build.warm
    build.harness(SIGNATURE)
    assert (cold, build.warm) == (False, True)


def test_a_compile_error_in_the_project_fails_the_build_with_paths_relative_to_it(workspace):
    build, _ = project_build(workspace, (101, "project-harness-user-error", ""))
    assert build.harness(SIGNATURE) == BuildFailed(
        (
            "src/lib.rs:20:26: error[E0425]: cannot find value `account_idx` in this scope",
            "    help: a local variable with a similar name exists: `account_id`",
        )
    )


def test_a_method_the_crate_lacks_is_built_again_without_the_user_target(workspace):
    build, cargo = project_build(workspace, (101, "project-harness-missing-method", ""), BUILT)
    build.harness(SIGNATURE)
    bridge = (build_directory(workspace) / "harness/main.rs").read_text()
    assert len(cargo.builds) == 2
    assert "cs_runner::Entry::Unavailable" in bridge


def test_a_method_the_crate_lacks_is_named_in_the_projects_terms(workspace):
    build, _ = project_build(workspace, (101, "project-harness-missing-method", ""), BUILT)
    build.harness(SIGNATURE)
    bridge = (build_directory(workspace) / "harness/main.rs").read_text()
    assert "no method named `transfer` found for mutable reference `&mut Bank`" in bridge


def test_a_project_without_a_manifest_fails_the_build(workspace):
    (workspace / "projects" / SLUG / "Cargo.toml").unlink()
    build, _ = project_build(workspace)
    assert build.harness(SIGNATURE) == BuildFailed(("Cargo.toml is missing",))


def test_a_manifest_without_a_package_name_fails_the_build(workspace):
    (workspace / "projects" / SLUG / "Cargo.toml").write_text("[package]\n")
    build, _ = project_build(workspace)
    assert build.harness(SIGNATURE) == BuildFailed(
        ("Cargo.toml names no package: [package] needs a name",)
    )


def test_cargo_refusing_the_projects_manifest_fails_the_build(workspace):
    stderr = "error: failed to parse manifest at `{root}/projects/bank-project-rust/Cargo.toml`\n"
    build, _ = project_build(workspace, (101, "built", stderr))
    assert build.harness(SIGNATURE) == BuildFailed(
        ("error: failed to parse manifest at `Cargo.toml`",)
    )


def test_cargo_failing_elsewhere_is_an_environment_error(workspace):
    build, _ = project_build(workspace, (101, "built", "error: no space left on device\n"))
    with pytest.raises(RunnerStartError, match="exit code 101"):
        build.harness(SIGNATURE)


# the suite


def targets(built) -> list[tuple[str, bool, UserError | None]]:
    return [(target.path, target.binary is not None, target.error) for target in built.targets]


def test_every_test_target_is_listed_in_path_order(workspace):
    build, _ = project_build(workspace, SUITE)
    assert [target.path for target in build.tests(()).targets] == [
        "src/lib.rs",
        "tests/broken.rs",
        "tests/statuses.rs",
    ]


def test_a_target_that_built_gets_a_private_copy_of_its_binary(workspace):
    build, _ = project_build(workspace, SUITE)
    built = build.tests(())
    statuses = next(target for target in built.targets if target.path == "tests/statuses.rs")
    assert statuses.binary is not None
    assert statuses.binary.parent == built.scratch


def test_a_target_that_does_not_compile_has_its_compile_error(workspace):
    build, _ = project_build(workspace, SUITE)
    broken = build.tests(()).targets[1]
    assert broken == SuiteTarget(
        "tests/broken.rs",
        error=UserError(
            "CompileError",
            "tests/broken.rs:3:28: error[E0308]: mismatched types",
            "    expected `i32`, found `&str`",
        ),
    )


def test_the_library_and_its_unit_tests_report_one_error_once(workspace):
    build, _ = project_build(workspace, (101, "project-suite-library-error", ""))
    assert targets(build.tests(())) == [
        (
            "src/lib.rs",
            False,
            UserError(
                "CompileError",
                "src/lib.rs:20:26: error[E0425]: cannot find value `account_idx` in this scope",
                "    help: a local variable with a similar name exists: `account_id`",
            ),
        )
    ]


def test_an_excluded_target_is_neither_listed_nor_reported(workspace):
    build, _ = project_build(workspace, SUITE)
    built = build.tests(("tests/broken.rs", "tests/statuses.rs"))
    assert [target.path for target in built.targets] == ["src/lib.rs"]


def test_the_suite_builds_the_crates_library_and_tests_and_keeps_going(workspace):
    build, cargo = project_build(workspace, SUITE)
    build.tests(())
    ((arguments, _, _),) = cargo.builds
    position = arguments.index("-p")
    assert arguments[position : position + 5] == ["-p", "bank", "--lib", "--tests", "--keep-going"]


def test_the_suite_keeps_a_bridge_the_grading_wrote(workspace):
    build, _ = project_build(workspace, BUILT, SUITE)
    build.harness(SIGNATURE)
    bridge = (build_directory(workspace) / "harness/main.rs").read_text()
    build.tests(())
    assert (build_directory(workspace) / "harness/main.rs").read_text() == bridge


def test_a_suite_before_any_grading_gives_the_harness_a_placeholder(workspace):
    build, _ = project_build(workspace, SUITE)
    build.tests(())
    assert (build_directory(workspace) / "harness/main.rs").read_text() == "fn main() {}\n"


def test_a_suite_of_a_project_without_a_manifest_cannot_build(workspace):
    (workspace / "projects" / SLUG / "Cargo.toml").unlink()
    build, _ = project_build(workspace)
    with pytest.raises(ProjectBuildError, match=r"Cargo\.toml is missing"):
        build.tests(())
