"""Cargo's JSON output, recorded from real builds of two-sum (tests/.../rust/recorded): the
workspace path is written `{root}`."""

import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.bridge import Unavailable
from coding_study.adapters.languages.rust.build_files import (
    RELEASE_PROFILE,
    CompilerError,
    compiler_errors,
    executable,
    load_error,
    package_manifest,
    profile_arguments,
    workspace_manifest,
    workspace_members,
)

RECORDED = Path(__file__).parent / "recorded"
ROOT = Path("/ws")
BUILD = ROOT / ".cs/build/rust"
USER_FILE = ROOT / "rust/practice/two_sum.rs"
BRIDGE_FILE = BUILD / "test/two_sum/main.rs"


def recorded(name: str) -> str:
    return (RECORDED / f"{name}.jsonl").read_text().replace("{root}", str(ROOT))


def only_error(name: str) -> CompilerError:
    (error,) = compiler_errors(recorded(name), BUILD)
    return error


def user_load_error(name: str) -> Unavailable:
    return load_error(only_error(name), "user", "two_sum.rs")


def test_a_successful_build_names_its_binary():
    assert executable(recorded("built"), "test_two_sum") == (
        ROOT / ".cs/build/rust/target/aarch64-apple-darwin/release/test_two_sum"
    )
    assert executable(recorded("built"), "verify_two_sum") is None


def test_an_error_in_the_users_file_is_located_there():
    error = only_error("user-error")
    assert (error.path, error.line, error.column, error.code) == (USER_FILE, 11, 5, "E0425")


def test_an_error_in_the_bridge_is_located_by_its_primary_span_only():
    """The secondary span names the user's similarly named function."""
    assert only_error("misnamed").path == BRIDGE_FILE


def test_summaries_without_spans_are_not_errors():
    assert len(compiler_errors(recorded("user-error"), BUILD)) == 1


def test_a_missing_function_is_symbol_not_found_with_the_compilers_hint():
    assert user_load_error("misnamed") == Unavailable(
        "SymbolNotFound",
        "cannot find function `two_sum` in `two_sum.rs`; "
        "a function with a similar name exists: `two_summ`",
    )


def test_a_private_function_says_to_make_it_pub():
    assert user_load_error("private") == Unavailable(
        "SymbolNotFound", "function `two_sum` is private; declare it pub"
    )


def test_a_parameter_of_another_type_names_the_parameter():
    assert user_load_error("parameter-type") == Unavailable(
        "SignatureMismatch",
        "mismatched types: parameter `nums` is `&[i32]`, the signature declares `Vec<i32>`",
    )


def test_a_result_of_another_type_names_both_types():
    assert user_load_error("result-type") == Unavailable(
        "SignatureMismatch",
        "mismatched types: the result is `Vec<usize>`, the signature declares `Vec<i32>`",
    )


def test_an_error_shows_its_location_message_and_label():
    assert only_error("user-error").shown("rust/practice/two_sum.rs") == (
        "rust/practice/two_sum.rs:11:5: error[E0425]: cannot find value `nil` in this scope",
        "    not found in this scope",
    )


def test_module_paths_in_types_are_the_users_names():
    error = CompilerError(BRIDGE_FILE, 1, 1, "E0599", "no method for `user::LRUCache`", "", ())
    assert load_error(error, "user", "lru_cache.rs").message == "no method for `LRUCache`"


def test_the_workspace_lists_each_harness_package(tmp_path):
    for package in ("test/two_sum", "bench/lru_cache", "verify/two_sum"):
        (tmp_path / package).mkdir(parents=True)
        (tmp_path / package / "Cargo.toml").write_text("")
    (tmp_path / "ref/two_sum").mkdir(parents=True)
    members = workspace_members(tmp_path)
    assert members == ["bench/lru_cache", "test/two_sum", "verify/two_sum"]
    document = tomllib.loads(workspace_manifest(members))
    assert document["workspace"]["members"] == members
    assert document["profile"]["release"]["overflow-checks"] is True


def test_a_harness_package_links_the_runner_crates_of_the_runtime():
    document = tomllib.loads(package_manifest("test_two_sum", "../../../runtime/runners/rust"))
    assert document["bin"] == [{"name": "test_two_sum", "path": "main.rs"}]
    assert document["dependencies"]["cs_runner"] == {
        "path": "../../../runtime/runners/rust/cs_runner"
    }


@pytest.mark.parametrize("setting", sorted(RELEASE_PROFILE))
def test_the_release_profile_is_also_passed_on_the_command_line(setting):
    arguments = profile_arguments()
    assert f"profile.release.{setting}={RELEASE_PROFILE[setting]}" in arguments
